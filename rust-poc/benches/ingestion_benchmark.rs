use criterion::{criterion_group, criterion_main, Criterion, BenchmarkId};
use webmacs_rust_poc::models::{DatapointCreate, DatapointBatch};
use uuid::Uuid;

fn generate_batch(size: usize) -> DatapointBatch {
    let datapoints = (0..size)
        .map(|i| DatapointCreate {
            value: 20.0 + i as f64 * 0.1,
            event_public_id: Uuid::new_v4(),
        })
        .collect();
    
    DatapointBatch { datapoints }
}

fn benchmark_serialization(c: &mut Criterion) {
    let mut group = c.benchmark_group("serialization");
    
    for size in [10, 50, 100, 250, 500].iter() {
        let batch = generate_batch(*size);
        
        group.bench_with_input(BenchmarkId::new("json", size), size, |b, _| {
            b.iter(|| serde_json::to_string(&batch).unwrap())
        });
    }
    
    group.finish();
}

fn benchmark_datapoint_creation(c: &mut Criterion) {
    let mut group = c.benchmark_group("datapoint_creation");
    
    for size in [10, 50, 100, 250, 500].iter() {
        group.bench_with_input(BenchmarkId::new("create", size), size, |b, &size| {
            b.iter(|| {
                let _batch = generate_batch(size);
            })
        });
    }
    
    group.finish();
}

criterion_group!(benches, benchmark_serialization, benchmark_datapoint_creation);
criterion_main!(benches);
