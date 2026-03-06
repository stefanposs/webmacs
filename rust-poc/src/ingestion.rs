use crate::models::{Datapoint, DatapointBatch, WebSocketMessage, Result, WebmacsError};
use sqlx::PgPool;
use tokio::sync::broadcast;
use tracing::{info, warn, error, instrument};
use uuid::Uuid;
use std::time::Instant;

pub struct IngestionService {
    db_pool: PgPool,
    ws_broadcaster: broadcast::Sender<WebSocketMessage>,
}

impl IngestionService {
    pub fn new(db_pool: PgPool) -> Self {
        let (ws_broadcaster, _) = broadcast::channel(1000);
        
        Self {
            db_pool,
            ws_broadcaster,
        }
    }
    
    pub async fn start(&self) -> Result<()> {
        info!("Ingestion service started");
        
        // In a real implementation, this would listen for HTTP requests
        // For PoC, we'll run a simple loop
        loop {
            tokio::time::sleep(tokio::time::Duration::from_secs(1)).await;
        }
    }
    
    #[instrument(skip(self, batch))]
    pub async fn ingest_datapoints(&self, batch: DatapointBatch) -> Result<Vec<Uuid>> {
        let start_time = Instant::now();
        let batch_size = batch.datapoints.len();
        
        info!("Processing batch of {} datapoints", batch_size);
        
        if batch_size == 0 {
            return Err(WebmacsError::Validation {
                message: "Empty batch not allowed".to_string(),
            });
        }

        if batch_size > 500 {
            return Err(WebmacsError::Validation {
                message: format!("Batch size {} exceeds maximum of 500", batch_size),
            });
        }
        
        // Get active experiment (simplified for PoC)
        let active_experiment = self.get_active_experiment().await
            .map_err(|e| WebmacsError::Database(format!("Failed to get active experiment: {}", e).into()))?;
        
        // Convert to datapoints with generated IDs and timestamps
        let datapoints: Vec<Datapoint> = batch
            .datapoints
            .into_iter()
            .map(|dp| dp.into_datapoint(active_experiment))
            .collect();
        
        // Parallel processing of side effects
        let (db_result, webhook_result, rule_result) = tokio::join!(
            self.persist_batch(&datapoints),
            self.dispatch_webhooks(&datapoints),
            self.evaluate_rules(&datapoints)
        );
        
        // Handle results
        let ids = db_result
            .map_err(|e| WebmacsError::Database(format!("Failed to persist batch: {}", e).into()))?;
        
        if let Err(e) = webhook_result {
            warn!("Webhook dispatch failed: {}", e);
        }
        
        if let Err(e) = rule_result {
            warn!("Rule evaluation failed: {}", e);
        }
        
        // Non-blocking WebSocket broadcast
        self.broadcast_to_websockets(datapoints).await;
        
        let duration = start_time.elapsed();
        info!(
            "Processed {} datapoints in {:?} ({:.1} dp/s)",
            batch_size,
            duration,
            batch_size as f64 / duration.as_secs_f64()
        );
        
        Ok(ids)
    }
    
    #[instrument(skip(self, datapoints))]
    async fn persist_batch(&self, datapoints: &[Datapoint]) -> Result<Vec<Uuid>> {
        let start = Instant::now();
        
        let mut tx = self.db_pool.begin().await
            .map_err(|e| WebmacsError::Database(format!("Failed to begin transaction: {}", e).into()))?;
        
        // Prepare arrays for bulk insert using PostgreSQL UNNEST
        let public_ids: Vec<Uuid> = datapoints.iter().map(|dp| dp.public_id).collect();
        let values: Vec<f64> = datapoints.iter().map(|dp| dp.value).collect();
        let timestamps: Vec<chrono::DateTime<chrono::Utc>> = datapoints.iter().map(|dp| dp.timestamp).collect();
        let event_ids: Vec<Uuid> = datapoints.iter().map(|dp| dp.event_public_id).collect();
        let experiment_ids: Vec<Option<Uuid>> = datapoints.iter().map(|dp| dp.experiment_public_id).collect();
        
        // Use UNNEST for efficient bulk insert with compile-time verification
        sqlx::query!(
            r#"
            INSERT INTO datapoints (public_id, value, timestamp, event_public_id, experiment_public_id)
            SELECT * FROM UNNEST($1::uuid[], $2::float8[], $3::timestamptz[], $4::uuid[], $5::uuid[])
            "#,
            &public_ids as &[Uuid],
            &values as &[f64],
            &timestamps as &[chrono::DateTime<chrono::Utc>],
            &event_ids as &[Uuid],
            &experiment_ids as &[Option<Uuid>]
        )
        .execute(&mut *tx)
        .await
        .map_err(|e| WebmacsError::Database(format!("Failed to execute batch insert: {}", e).into()))?;
            
        tx.commit().await
            .map_err(|e| WebmacsError::Database(format!("Failed to commit transaction: {}", e).into()))?;
        
        let duration = start.elapsed();
        info!(
            "Persisted {} datapoints in {:?} ({:.1} dp/s)",
            datapoints.len(),
            duration,
            datapoints.len() as f64 / duration.as_secs_f64()
        );
        
        Ok(public_ids)
    }
    
    async fn get_active_experiment(&self) -> Result<Option<Uuid>> {
        let result = sqlx::query_scalar!(
            "SELECT public_id FROM experiments WHERE stopped_on IS NULL ORDER BY started_on DESC LIMIT 1"
        )
        .fetch_optional(&self.db_pool)
        .await?;
        
        Ok(result)
    }
    
    async fn dispatch_webhooks(&self, datapoints: &[Datapoint]) -> Result<()> {
        // Simplified webhook dispatch for PoC
        info!("Would dispatch webhooks for {} datapoints", datapoints.len());
        
        // Simulate webhook dispatch latency
        tokio::time::sleep(tokio::time::Duration::from_millis(10)).await;
        
        Ok(())
    }
    
    async fn evaluate_rules(&self, datapoints: &[Datapoint]) -> Result<()> {
        // Simplified rule evaluation for PoC
        info!("Would evaluate rules for {} datapoints", datapoints.len());
        
        // Simulate rule evaluation latency
        tokio::time::sleep(tokio::time::Duration::from_millis(5)).await;
        
        Ok(())
    }
    
    async fn broadcast_to_websockets(&self, datapoints: Vec<Datapoint>) {
        let message = WebSocketMessage {
            message_type: "datapoints_batch".to_string(),
            datapoints,
        };
        
        if let Err(_) = self.ws_broadcaster.send(message) {
            warn!("WebSocket broadcast failed: no active receivers");
        }
    }
    
    pub fn get_websocket_receiver(&self) -> broadcast::Receiver<WebSocketMessage> {
        self.ws_broadcaster.subscribe()
    }
}
