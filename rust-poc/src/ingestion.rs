use crate::models::{Datapoint, DatapointBatch, WebSocketMessage, Result};
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
        
        // Get active experiment (simplified for PoC)
        let active_experiment = self.get_active_experiment().await?;
        
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
        let ids = db_result?;
        
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
        
        // Use PostgreSQL COPY for maximum throughput
        let mut tx = self.db_pool.begin().await?;
        
        // Build VALUES clause for batch insert
        let mut query = String::from(
            "INSERT INTO datapoints (public_id, value, timestamp, event_public_id, experiment_public_id) VALUES "
        );
        
        let mut params = Vec::new();
        for (i, dp) in datapoints.iter().enumerate() {
            if i > 0 {
                query.push_str(", ");
            }
            let base = i * 5;
            query.push_str(&format!(
                "(${}, ${}, ${}, ${}, ${})",
                base + 1, base + 2, base + 3, base + 4, base + 5
            ));
            
            params.extend([
                Box::new(dp.public_id) as Box<dyn sqlx::Encode<sqlx::Postgres> + Send + Sync>,
                Box::new(dp.value),
                Box::new(dp.timestamp),
                Box::new(dp.event_public_id),
                Box::new(dp.experiment_public_id),
            ]);
        }
        
        // Execute batch insert
        sqlx::query(&query)
            .bind_all(params)
            .execute(&mut *tx)
            .await?;
            
        tx.commit().await?;
        
        let duration = start.elapsed();
        info!(
            "Persisted {} datapoints in {:?} ({:.1} dp/s)",
            datapoints.len(),
            duration,
            datapoints.len() as f64 / duration.as_secs_f64()
        );
        
        Ok(datapoints.iter().map(|dp| dp.public_id).collect())
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
        
        if let Err(e) = self.ws_broadcaster.send(message) {
            warn!("WebSocket broadcast failed: {}", e);
        }
    }
    
    pub fn get_websocket_receiver(&self) -> broadcast::Receiver<WebSocketMessage> {
        self.ws_broadcaster.subscribe()
    }
}

// Extension trait to bind multiple parameters
trait QueryExt {
    fn bind_all<T>(self, params: Vec<T>) -> Self
    where
        T: sqlx::Encode<sqlx::Postgres> + Send + Sync;
}

impl<'a> QueryExt for sqlx::query::Query<'a, sqlx::Postgres, sqlx::postgres::PgArguments> {
    fn bind_all<T>(mut self, params: Vec<T>) -> Self
    where
        T: sqlx::Encode<sqlx::Postgres> + Send + Sync,
    {
        for param in params {
            self = self.bind(param);
        }
        self
    }
}
