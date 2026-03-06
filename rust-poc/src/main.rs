use anyhow::Result;
use clap::Parser;
use std::env;
use tracing::{info, warn};

mod ingestion;
mod models;
mod websocket;
mod benchmark;

use ingestion::IngestionService;
use websocket::WebSocketServer;

#[derive(Parser)]
#[command(name = "webmacs-rust-poc")]
#[command(about = "WebMACS Rust Performance Proof of Concept")]
struct Cli {
    #[arg(short, long, default_value = "info")]
    log_level: String,
    
    #[arg(short, long, default_value = "localhost:3000")]
    bind_addr: String,
    
    #[arg(long)]
    benchmark: bool,
    
    #[arg(long, default_value = "postgresql://webmacs:webmacs@localhost:5432/webmacs")]
    database_url: String,
}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();
    
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_max_level(cli.log_level.parse().unwrap_or(tracing::Level::INFO))
        .init();
        
    info!("Starting WebMACS Rust PoC");
    
    if cli.benchmark {
        info!("Running benchmark mode");
        benchmark::run_performance_comparison().await?;
        return Ok(());
    }
    
    // Initialize database connection pool
    let db_pool = sqlx::PgPool::connect(&cli.database_url).await?;
    info!("Connected to database");
    
    // Initialize services
    let ingestion_service = IngestionService::new(db_pool.clone());
    let websocket_server = WebSocketServer::new();
    
    // Start WebSocket server
    let ws_handle = tokio::spawn(async move {
        websocket_server.start(&cli.bind_addr).await
    });
    
    // Start ingestion service
    let ingestion_handle = tokio::spawn(async move {
        ingestion_service.start().await
    });
    
    info!("Services started on {}", cli.bind_addr);
    
    // Wait for shutdown signal
    tokio::select! {
        _ = tokio::signal::ctrl_c() => {
            info!("Received shutdown signal");
        }
        result = ws_handle => {
            warn!("WebSocket server exited: {:?}", result);
        }
        result = ingestion_handle => {
            warn!("Ingestion service exited: {:?}", result);
        }
    }
    
    Ok(())
}
