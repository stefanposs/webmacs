#!/bin/bash

# WebMACS Rust Performance Benchmark Script
set -e

echo "🦀 WebMACS Rust Performance Benchmark"
echo "======================================="

# Check if database is running
echo "📊 Checking database connection..."
if ! pg_isready -h localhost -p 5432 -U webmacs 2>/dev/null; then
    echo "❌ PostgreSQL not available. Starting with Docker..."
    docker-compose -f ../docker-compose.yml up -d db
    echo "⏳ Waiting for database..."
    sleep 10
fi

echo "✅ Database ready"

# Build the project
echo "🔨 Building Rust project..."
cargo build --release

# Run criterion benchmarks
echo "🚀 Running micro-benchmarks..."
cargo bench

# Run application-level benchmarks
echo "📈 Running application benchmarks..."
DATABASE_URL="postgresql://webmacs:webmacs@localhost:5432/webmacs" \
    cargo run --release -- --benchmark

echo ""
echo "✅ Benchmark complete!"
echo "📁 Check target/criterion/report/index.html for detailed micro-benchmark results"
echo "📁 Check benchmark_results.json for performance comparison"
