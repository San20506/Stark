# Tasks: Implement STARK Orchestration

## 1. Core STARK Class
- [x] 1.1 Create `core/main.py` with STARK class skeleton
- [x] 1.2 Implement singleton pattern with `get_stark()` factory function
- [x] 1.3 Add configuration loading from `core/config.py`
- [x] 1.4 Implement lazy loading for heavy modules (model, memory)

## 2. Module Integration
- [x] 2.1 Integrate TaskDetector for query classification
- [x] 2.2 Integrate NeuromorphicMemory for experience storage/recall
- [x] 2.3 Integrate AdapterManager for LoRA adapter switching (placeholder)
- [x] 2.4 Integrate ContinualLearner for background training
- [x] 2.5 Integrate InferenceEngine for model inference (via Ollama)
- [x] 2.6 Integrate capability modules (placeholder, error_debugger ready)

## 3. Inference Pipeline
- [x] 3.1 Implement `predict(query: str) -> Dict` method
- [x] 3.2 Implement `predict_stream(query: str) -> Generator` method
- [x] 3.3 Build complete pipeline: detect task → recall memories → inference → store experience
- [x] 3.4 Add latency tracking for each pipeline stage

## 4. Lifecycle Management
- [x] 4.1 Implement `start()` method to initialize all modules
- [x] 4.2 Implement `stop()` method for graceful shutdown
- [x] 4.3 Start/stop ContinualLearner background thread
- [x] 4.4 Save memory state on shutdown

## 5. Status & Monitoring
- [x] 5.1 Implement `status() -> Dict` method with system info
- [x] 5.2 Implement `health_check() -> Dict` method to verify all modules
- [x] 5.3 Add uptime, query count tracking
- [ ] 5.4 Integrate with `utils/metrics.py` for TensorBoard logging

## 6. Error Handling
- [x] 6.1 Add try-except around inference pipeline
- [x] 6.2 Implement graceful degradation for module failures
- [x] 6.3 Add structured error logging via `utils/logger.py`
- [ ] 6.4 Implement retry logic for transient errors

## 7. Testing
- [x] 7.1 Create `tests/test_orchestration.py`
- [x] 7.2 Test singleton pattern
- [x] 7.3 Test inference pipeline end-to-end
- [x] 7.4 Test startup/shutdown sequence
- [x] 7.5 Test error handling and recovery

## Summary
- **Created**: `core/main.py` (~420 lines)
- **Created**: `tests/test_orchestration.py` (~180 lines)
- **Tests**: 13 tests, all passing
- **Status**: Module 8 complete, pending minor enhancements (metrics integration, retry logic)
