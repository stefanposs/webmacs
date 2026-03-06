use crate::models::{WebSocketMessage, Result};
use axum::{
    extract::{
        ws::{WebSocket, Message},
        WebSocketUpgrade,
    },
    response::Response,
    routing::get,
    Router,
};
use std::sync::Arc;
use tokio::sync::broadcast;
use tracing::{info, warn, error};

pub struct WebSocketServer {
    clients: Arc<std::sync::Mutex<Vec<broadcast::Sender<WebSocketMessage>>>>,
}

impl WebSocketServer {
    pub fn new() -> Self {
        Self {
            clients: Arc::new(std::sync::Mutex::new(Vec::new())),
        }
    }
    
    pub async fn start(&self, bind_addr: &str) -> Result<()> {
        let app = Router::new()
            .route("/ws/datapoints/stream", get(websocket_handler))
            .with_state(self.clients.clone());
            
        let listener = tokio::net::TcpListener::bind(bind_addr).await
            .map_err(|e| crate::models::WebmacsError::Validation { 
                message: format!("Failed to bind to {}: {}", bind_addr, e) 
            })?;
            
        info!("WebSocket server listening on {}", bind_addr);
        
        axum::serve(listener, app).await
            .map_err(|e| crate::models::WebmacsError::Validation {
                message: format!("Server error: {}", e)
            })?;
            
        Ok(())
    }
    
    pub async fn broadcast(&self, message: WebSocketMessage) {
        let clients = self.clients.lock().unwrap();
        let mut disconnected = Vec::new();
        
        for (i, client) in clients.iter().enumerate() {
            if let Err(_) = client.send(message.clone()) {
                disconnected.push(i);
            }
        }
        
        // Remove disconnected clients
        drop(clients);
        if !disconnected.is_empty() {
            let mut clients = self.clients.lock().unwrap();
            for &i in disconnected.iter().rev() {
                clients.remove(i);
            }
            info!("Removed {} disconnected clients", disconnected.len());
        }
    }
}

async fn websocket_handler(
    ws: WebSocketUpgrade,
    axum::extract::State(clients): axum::extract::State<Arc<std::sync::Mutex<Vec<broadcast::Sender<WebSocketMessage>>>>>,
) -> Response {
    ws.on_upgrade(|socket| handle_websocket(socket, clients))
}

async fn handle_websocket(
    socket: WebSocket,
    clients: Arc<std::sync::Mutex<Vec<broadcast::Sender<WebSocketMessage>>>>,
) {
    let (sender, mut receiver) = socket.split();
    let (tx, mut rx) = broadcast::channel::<WebSocketMessage>(100);
    
    // Add client to the list
    {
        let mut client_list = clients.lock().unwrap();
        client_list.push(tx.clone());
    }
    
    info!("WebSocket client connected");
    
    // Send connection acknowledgment
    let ack_message = WebSocketMessage {
        message_type: "connected".to_string(),
        datapoints: Vec::new(),
    };
    
    if let Ok(json) = serde_json::to_string(&ack_message) {
        if let Err(e) = sender.send(Message::Text(json)).await {
            warn!("Failed to send connection ack: {}", e);
            return;
        }
    }
    
    // Handle incoming messages (ping/pong)
    let ping_task = tokio::spawn(async move {
        while let Some(msg) = receiver.recv().await {
            match msg {
                Ok(Message::Text(text)) => {
                    if text.contains("ping") {
                        let pong = r#"{"type":"pong"}"#;
                        if let Err(e) = sender.send(Message::Text(pong.to_string())).await {
                            error!("Failed to send pong: {}", e);
                            break;
                        }
                    }
                }
                Ok(Message::Close(_)) => {
                    info!("WebSocket client disconnected");
                    break;
                }
                Err(e) => {
                    error!("WebSocket error: {}", e);
                    break;
                }
                _ => {}
            }
        }
    });
    
    // Handle outgoing broadcasts
    let broadcast_task = tokio::spawn(async move {
        while let Ok(message) = rx.recv().await {
            if let Ok(json) = serde_json::to_string(&message) {
                if sender.send(Message::Text(json)).await.is_err() {
                    break;
                }
            }
        }
    });
    
    // Wait for either task to complete
    tokio::select! {
        _ = ping_task => {},
        _ = broadcast_task => {},
    }
    
    info!("WebSocket connection handler finished");
}
