use crate::models::{WebSocketMessage, Result, WebmacsError, JwtClaims, AuthenticatedUser};
use axum::{
    extract::{
        ws::{WebSocket, Message},
        WebSocketUpgrade, Query,
    },
    response::Response,
    routing::get,
    Router,
    http::{StatusCode, HeaderMap},
};
use std::sync::Arc;
use tokio::sync::{broadcast, RwLock};
use tracing::{info, warn, error};
use serde::Deserialize;
use jsonwebtoken::{decode, DecodingKey, Validation, Algorithm};

#[derive(Debug, Deserialize)]
struct WebSocketQuery {
    token: Option<String>,
}

pub struct WebSocketServer {
    clients: Arc<RwLock<Vec<broadcast::Sender<WebSocketMessage>>>>,
    jwt_secret: String,
}

impl WebSocketServer {
    pub fn new(jwt_secret: String) -> Self {
        Self {
            clients: Arc::new(RwLock::new(Vec::new())),
            jwt_secret,
        }
    }
    
    pub async fn start(&self, bind_addr: &str) -> Result<()> {
        let app = Router::new()
            .route("/ws/datapoints/stream", get(websocket_handler))
            .with_state((self.clients.clone(), self.jwt_secret.clone()));
            
        let listener = tokio::net::TcpListener::bind(bind_addr).await
            .map_err(|e| WebmacsError::Configuration { 
                message: format!("Failed to bind to {}: {}", bind_addr, e) 
            })?;
            
        info!("WebSocket server listening on {}", bind_addr);
        
        axum::serve(listener, app).await
            .map_err(|e| WebmacsError::Configuration {
                message: format!("Server error: {}", e)
            })?;
            
        Ok(())
    }
    
    pub async fn broadcast(&self, message: WebSocketMessage) {
        let clients = self.clients.read().await;
        let mut disconnected = Vec::new();
        
        for (i, client) in clients.iter().enumerate() {
            if let Err(_) = client.send(message.clone()) {
                disconnected.push(i);
            }
        }
        
        // Remove disconnected clients
        drop(clients);
        if !disconnected.is_empty() {
            let mut clients = self.clients.write().await;
            for &i in disconnected.iter().rev() {
                if i < clients.len() {
                    clients.remove(i);
                }
            }
            info!("Removed {} disconnected clients", disconnected.len());
        }
    }
}

async fn websocket_handler(
    ws: WebSocketUpgrade,
    Query(params): Query<WebSocketQuery>,
    axum::extract::State((clients, jwt_secret)): axum::extract::State<(
        Arc<RwLock<Vec<broadcast::Sender<WebSocketMessage>>>>,
        String,
    )>,
) -> Result<Response, StatusCode> {
    // Authenticate the WebSocket connection
    let token = params.token.ok_or(StatusCode::UNAUTHORIZED)?;
    let _user = authenticate_token(&token, &jwt_secret)?;
    
    Ok(ws.on_upgrade(move |socket| handle_websocket(socket, clients, _user)))
}

fn authenticate_token(token: &str, secret: &str) -> Result<AuthenticatedUser, StatusCode> {
    let decoding_key = DecodingKey::from_secret(secret.as_ref());
    let validation = Validation::new(Algorithm::HS256);
    
    let token_data = decode::<JwtClaims>(token, &decoding_key, &validation)
        .map_err(|_| StatusCode::UNAUTHORIZED)?;
    
    let user_id = token_data.claims.sub.parse()
        .map_err(|_| StatusCode::UNAUTHORIZED)?;
    
    Ok(AuthenticatedUser {
        user_id,
        username: token_data.claims.username,
        admin: token_data.claims.admin,
    })
}

async fn handle_websocket(
    mut socket: WebSocket,
    clients: Arc<RwLock<Vec<broadcast::Sender<WebSocketMessage>>>>,
    _user: AuthenticatedUser,
) {
    let (tx, mut rx) = broadcast::channel::<WebSocketMessage>(100);
    
    // Add client to the list
    {
        let mut client_list = clients.write().await;
        client_list.push(tx.clone());
    }
    
    info!("WebSocket client connected (user: {})", _user.username);
    
    // Send connection acknowledgment
    let ack_message = WebSocketMessage {
        message_type: "connected".to_string(),
        datapoints: Vec::new(),
    };
    
    if let Ok(json) = serde_json::to_string(&ack_message) {
        if let Err(e) = socket.send(Message::Text(json)).await {
            warn!("Failed to send connection ack: {}", e);
            return;
        }
    }
    
    // Handle incoming messages (ping/pong)
    let ping_task = tokio::spawn(async move {
        while let Some(msg) = socket.recv().await {
            match msg {
                Ok(Message::Text(text)) => {
                    if text.contains("ping") {
                        let pong = r#"{"type":"pong"}"#;
                        if let Err(e) = socket.send(Message::Text(pong.to_string())).await {
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
    let mut socket_clone = socket;
    let broadcast_task = tokio::spawn(async move {
        while let Ok(message) = rx.recv().await {
            if let Ok(json) = serde_json::to_string(&message) {
                if socket_clone.send(Message::Text(json)).await.is_err() {
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
