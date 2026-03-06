use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};
use uuid::Uuid;

#[derive(Debug, Clone, Serialize, Deserialize, sqlx::FromRow)]
pub struct Datapoint {
    pub public_id: Uuid,
    pub value: f64,
    pub timestamp: DateTime<Utc>,
    pub event_public_id: Uuid,
    pub experiment_public_id: Option<Uuid>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DatapointCreate {
    pub value: f64,
    pub event_public_id: Uuid,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DatapointBatch {
    pub datapoints: Vec<DatapointCreate>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WebSocketMessage {
    pub message_type: String,
    pub datapoints: Vec<Datapoint>,
}

#[derive(Debug, thiserror::Error)]
pub enum WebmacsError {
    #[error("Database error: {0}")]
    Database(#[from] sqlx::Error),
    
    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
    
    #[error("WebSocket error: {0}")]
    WebSocket(#[from] tokio_tungsgenite::tungstenite::Error),
    
    #[error("Validation error: {message}")]
    Validation { message: String },
}

pub type Result<T> = std::result::Result<T, WebmacsError>;

impl DatapointCreate {
    pub fn into_datapoint(self, experiment_id: Option<Uuid>) -> Datapoint {
        Datapoint {
            public_id: Uuid::new_v4(),
            value: self.value,
            timestamp: Utc::now(),
            event_public_id: self.event_public_id,
            experiment_public_id: experiment_id,
        }
    }
}
