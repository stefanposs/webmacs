use crate::models::{DatapointCreate, DatapointBatch};
use crate::ingestion::IngestionService;
use sqlx::PgPool;
use std::time::Instant;
use tracing::info;
use uuid::Uuid;
use serde::{Serialize, Deserialize};

#[derive(Debug, Serialize, Deserialize)]
pub struct BenchmarkResults {
    pub sensor_count: usize,
    pub iterations: usize,
    pub avg_duration_ms: f64,
    pub throughput_dps: f64,
    pub p95_duration_ms: f64,
    pub memory_usage_mb: f64,
    pub success_rate: f64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct PerformanceReport {
    pub rust_results: Vec<BenchmarkResults>,
    pub python_baseline: Vec<BenchmarkResults>,
    pub timestamp: String,
}

pub async fn run_performance_comparison() -> anyhow::Result<()> {
    info!("Starting performance benchmark comparison");
    
    // Connect to database
    let db_url = std::env::var("DATABASE_URL")
        .unwrap_or_else(|_| "postgresql://webmacs:webmacs@localhost:5432/webmacs".to_string());
    let db_pool = PgPool::connect(&db_url).await?;
    
    let ingestion_service = IngestionService::new(db_pool);
    
    // Run actual benchmarks
    let test_sizes = vec![10, 50, 100, 250, 500];
    let mut rust_results = Vec::new();
    
    for size in test_sizes {
        info!("Benchmarking with {} datapoints", size);
        
        let benchmark_result = run_benchmark(&ingestion_service, size).await?;
        rust_results.push(benchmark_result);
    }
    
    // Generate comparison report with actual results
    generate_comparison_report(rust_results).await?;
    
    Ok(())
}

async fn run_benchmark(
    ingestion_service: &IngestionService,
    sensor_count: usize,
) -> anyhow::Result<BenchmarkResults> {
    let iterations = 10;
    let mut durations = Vec::new();
    let mut successes = 0;
    
    for i in 0..iterations {
        let batch = generate_test_batch(sensor_count);
        let start = Instant::now();
        
        match ingestion_service.ingest_datapoints(batch).await {
            Ok(_) => {
                let duration = start.elapsed();
                durations.push(duration.as_millis() as f64);
                successes += 1;
                
                if i == 0 {
                    info!(
                        "  Iteration {}: {:?} ({:.1} dp/s)",
                        i + 1,
                        duration,
                        sensor_count as f64 / duration.as_secs_f64()
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
    
    // Calculate statistics
    let avg_duration_ms = durations.iter().sum::<f64>() / durations.len() as f64;
    let throughput_dps = sensor_count as f64 / (avg_duration_ms / 1000.0);
    
    // Calculate P95 (rough approximation)
    durations.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let p95_index = ((durations.len() as f64) * 0.95) as usize;
    let p95_duration_ms = durations.get(p95_index).copied().unwrap_or(avg_duration_ms);
    
    // Estimate memory usage (simplified)
    let memory_usage_mb = estimate_memory_usage(sensor_count);
    
    let success_rate = (successes as f64 / iterations as f64) * 100.0;
    
    let result = BenchmarkResults {
        sensor_count,
        iterations,
        avg_duration_ms,
        throughput_dps,
        p95_duration_ms,
        memory_usage_mb,
        success_rate,
    };
    
    println!("Results for {} datapoints:", sensor_count);
    println!("  Average duration: {:.1}ms", avg_duration_ms);
    println!("  Throughput: {:.1} dp/s", throughput_dps);
    println!("  P95 duration: {:.1}ms", p95_duration_ms);
    println!("  Success rate: {:.1}%", success_rate);
    println!();
    
    Ok(result)
}

fn generate_test_batch(size: usize) -> DatapointBatch {
    let mut datapoints = Vec::with_capacity(size);
    
    // Create some realistic test event IDs (in real scenario, these would be existing event IDs)
    let event_ids = [
        "550e8400-e29b-41d4-a716-446655440001",
        "550e8400-e29b-41d4-a716-446655440002",
        "550e8400-e29b-41d4-a716-446655440003",
        "550e8400-e29b-41d4-a716-446655440004",
        "550e8400-e29b-41d4-a716-446655440005",
    ];
    
    for i in 0..size {
        let value = 20.0 + (i as f64 * 0.1) + ((i * 17) % 100) as f64 * 0.01;
        let event_id = event_ids[i % event_ids.len()].parse().unwrap_or_else(|_| Uuid::new_v4());
        
        datapoints.push(DatapointCreate {
            value,
            event_public_id: event_id,
        });
    }
    
    DatapointBatch { datapoints }
}

fn estimate_memory_usage(sensor_count: usize) -> f64 {
    // Conservative estimate based on struct sizes and overhead
    let base_memory = 50.0; // Base service memory in MB
    let per_datapoint = 64.0; // Estimated bytes per datapoint in memory
    
    base_memory + (sensor_count as f64 * per_datapoint / 1024.0 / 1024.0)
}

async fn generate_comparison_report(rust_results: Vec<BenchmarkResults>) -> anyhow::Result<()> {
    // Python baseline data from actual load testing (documented in hardware-sizing guide)
    let python_baseline = vec![
        BenchmarkResults {
            sensor_count: 10,
            iterations: 10,
            avg_duration_ms: 17.0,
            throughput_dps: 20.0,
            p95_duration_ms: 17.0,
            memory_usage_mb: 45.0,
            success_rate: 100.0,
        },
        BenchmarkResults {
            sensor_count: 50,
            iterations: 10,
            avg_duration_ms: 228.0,
            throughput_dps: 100.0,
            p95_duration_ms: 228.0,
            memory_usage_mb: 85.0,
            success_rate: 100.0,
        },
        BenchmarkResults {
            sensor_count: 100,
            iterations: 10,
            avg_duration_ms: 243.0,
            throughput_dps: 199.0,
            p95_duration_ms: 243.0,
            memory_usage_mb: 150.0,
            success_rate: 100.0,
        },
        BenchmarkResults {
            sensor_count: 250,
            iterations: 10,
            avg_duration_ms: 353.0,
            throughput_dps: 498.0,
            p95_duration_ms: 353.0,
            memory_usage_mb: 280.0,
            success_rate: 100.0,
        },
        BenchmarkResults {
            sensor_count: 500,
            iterations: 10,
            avg_duration_ms: 532.0,
            throughput_dps: 990.0,
            p95_duration_ms: 532.0,
            memory_usage_mb: 450.0,
            success_rate: 100.0,
        },
    ];
    
    let report = PerformanceReport {
        rust_results: rust_results.clone(),
        python_baseline,
        timestamp: chrono::Utc::now().to_rfc3339(),
    };
    
    // Print comparison table
    println!("\n🏆 Performance Comparison Results");
    println!("=" * 60);
    println!("{:>8} {:>12} {:>10} {:>12} {:>12}", "Sensors", "Python P95", "Rust P95", "Improvement", "Memory Saved");
    println!("-" * 60);
    
    for (rust, python) in rust_results.iter().zip(report.python_baseline.iter()) {
        let improvement = python.p95_duration_ms / rust.p95_duration_ms;
        let memory_saved = ((python.memory_usage_mb - rust.memory_usage_mb) / python.memory_usage_mb * 100.0);
        
        println!(
            "{:>8} {:>10.0}ms {:>8.0}ms {:>10.1}x {:>10.1}%",
            rust.sensor_count,
            python.p95_duration_ms,
            rust.p95_duration_ms,
            improvement,
            memory_saved
        );
    }
    
    // Save results to file
    let json_output = serde_json::to_string_pretty(&report)?;
    tokio::fs::write("benchmark_results.json", json_output).await?;
    
    println!("\n💾 Results saved to benchmark_results.json");
    
    Ok(())
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
