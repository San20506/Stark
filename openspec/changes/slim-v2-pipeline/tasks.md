## 1. Trim Loader
- [x] 1.1 `_load_modules_v2` inits diary, thread_state, reflection, Hebbian recall only

## 2. Slim Pipeline
- [x] 2.1 `_run_v2_pipeline` returns diary + `messages[-4:]` context (no appraisal/episode/graph)
- [x] 2.2 `_update_v2_state` updates thread state and triggers reflection only
- [x] 2.3 Keep call sites `455-461` and `552-557` intact

## 3. Verify
- [ ] 3.1 First-token latency ≤3s with full stack
- [ ] 3.2 Retrieval ≤100ms on 221-row episodic DB
