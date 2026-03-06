use crate::models::{DatapointCreate, DatapointBatch};
use crate::ingestion::IngestionService;
use sqlx::PgPool;
use std::time::Instant;
use tracing::info;
use uuid::Uuid;

pub async fn run_performance_comparison() -> anyhow::Result<()> {
    info!("Starting performance benchmark comparison");
    
    // Connect to database
    let db_url = std::env::var("DATABASE_URL")
        .unwrap_or_else(|_| "postgresql://webmacs:webmacs@localhost:5432/webmacs".to_string());
    let db_pool = PgPool::connect(&db_url).await?;
    
    let ingestion_service = IngestionService::new(db_pool);
    
    // Generate test data
    let test_sizes = vec![10, 50, 100, 250, 500];
    
    for size in test_sizes {
        info!("Benchmarking with {} datapoints", size);
        
        let batch = generate_test_batch(size);
        let iterations = 10;
        let mut total_duration = std::time::Duration::ZERO;
        
        for i in 0..iterations {
            let start = Instant::now();
            
            match ingestion_service.ingest_datapoints(batch.clone()).await {
                Ok(_) => {
                    let duration = start.elapsed();
                    total_duration += duration;
                    
                    if i == 0 {
                        info!(
                            "  Iteration {}: {:?} ({:.1} dp/s)",
                            i + 1,
                            duration,
                            size as f64 / duration.as_secs_f64()
                        );
                    }
                }
                Err(e) => {
                    eprintln!("Error in iteration {}: {}", i + 1, e);
                }
            }
            
            // Small delay between iterations
            tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
        }
        
        let avg_duration = total_duration / iterations;
        let throughput = size as f64 / avg_duration.as_secs_f64();
        
        println!("Results for {} datapoints:", size);
        println!("  Average duration: {:?}", avg_duration);
        println!("  Throughput: {:.1} dp/s", throughput);
        println!("  P95 estimate: {:?}", avg_duration * 95 / 50); // Rough P95 estimation
        println!();
    }
    
    Ok(())
}

fn generate_test_batch(size: usize) -> DatapointBatch {
    let mut datapoints = Vec::with_capacity(size);
    
    // Generate random-ish data
    for i in 0..size {
        let value = 20.0 + (i as f64 * 0.1) + ((i * 17) % 100) as f64 * 0.01;
        let event_id = Uuid::new_v4(); // In real scenario, these would be existing event IDs
        
        datapoints.push(DatapointCreate {
            value,
            event_public_id: event_id,
        });
    }
    
    DatapointBatch { datapoints }
}

// Comparative analysis functions
pub fn analyze_memory_usage() {
    info!("Memory usage analysis:");
    info!("  Rust struct sizes:");
    info!("    Datapoint: {} bytes", std::mem::size_of::<crate::models::Datapoint>());
    info!("    DatapointCreate: {} bytes", std::mem::size_of::<DatapointCreate>());
    info!("    DatapointBatch(100): ~{} bytes", 
          std::mem::size_of::<DatapointBatch>() + (100 * std::mem::size_of::<DatapointCreate>()));
}

pub fn compare_serialization_performance() {
    use std::time::Instant;
    
    let batch = generate_test_batch(100);
    let iterations = 1000;
    
    info!("Serialization performance comparison:");
    
    // JSON serialization
    let start = Instant::now();
    for _ in 0..iterations {
        let _ = serde_json::to_string(&batch).unwrap();
    }
    let json_duration = start.elapsed();
    
    info!("  JSON: {:?} per 100 items", json_duration / iterations);
    info!("  Estimated throughput: {:.1} batches/s", 
          iterations as f64 / json_duration.as_secs_f64());
}
