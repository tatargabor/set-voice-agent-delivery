## 1. Backchannel Filter

- [x] 1.1 Add `is_backchannel(text)` and `is_stop_word(text)` functions with Hungarian word lists and text normalization
- [x] 1.2 Modify `_stt_loop` SPEAKING state: check backchannel/stop before triggering barge-in
- [x] 1.3 Log backchannel_ignored and unknown_short_ignored events with the transcript text

## 2. Testing

- [x] 2.1 Unit tests for is_backchannel and is_stop_word (with punctuation, casing, etc.)
- [x] 2.2 Unit test: backchannel during SPEAKING does not trigger barge-in
- [x] 2.3 Unit test: stop word during SPEAKING triggers barge-in
- [x] 2.4 Unit test: 3+ word utterance during SPEAKING triggers barge-in
