#pragma once

#ifdef __cplusplus
extern "C" {
#endif

typedef struct yanmo_engine_t yanmo_engine_t;

// Lifecycle
yanmo_engine_t* yanmo_create(void);
void yanmo_destroy(yanmo_engine_t* engine);
int yanmo_init(yanmo_engine_t* engine, const char* lexicon_path, const char* radicals_path);
int yanmo_load_user_dict(yanmo_engine_t* engine, const char* user_dict_path);
int yanmo_load_bigram(yanmo_engine_t* engine, const char* bigram_path);
void yanmo_reset(yanmo_engine_t* engine);

// Key input & processing
// Returns 1 if key was consumed, 0 otherwise.
// If committing text, out_commit will be filled with null-terminated UTF-8 text.
int yanmo_feed_key(yanmo_engine_t* engine, 
                   const char* key, 
                   int is_shift, 
                   char* out_commit, 
                   int max_commit_len);

// Information queries
int yanmo_get_buffer(yanmo_engine_t* engine, char* out_buf, int max_len);
int yanmo_get_radical_hint(yanmo_engine_t* engine, char* out_buf, int max_len);
int yanmo_get_radical_buffer(yanmo_engine_t* engine, char* out_buf, int max_len);

// Status queries: mode (0:IDLE, 1:COMPOSING, 2:RADICAL)
int yanmo_get_status(yanmo_engine_t* engine, 
                     int* out_mode, 
                     int* out_total_cands, 
                     int* out_page_offset, 
                     int* out_active_row, 
                     int* out_is_expanded);

// Returns JSON array of candidate words for the specified row: ["你好", "拟好", ...]
int yanmo_get_row_candidates_json(yanmo_engine_t* engine, 
                                  int row_idx, 
                                  char* out_buf, 
                                  int max_len);

// Returns JSON array of top candidate words: ["你好", "拟好", ...] up to max_cands
int yanmo_get_candidates_json(yanmo_engine_t* engine,
                              int max_cands,
                              char* out_buf,
                              int max_len);

// Save dynamically learned bigram transitions to TSV
int yanmo_save_user_bigram(yanmo_engine_t* engine, const char* filepath);

// Candidate selection & commit
int yanmo_select_candidate(yanmo_engine_t* engine, 
                           int index, 
                           char* out_commit, 
                           int max_commit_len);
int yanmo_get_committed_text(yanmo_engine_t* engine, char* out_buf, int max_len);
void yanmo_clear_committed_text(yanmo_engine_t* engine);
int yanmo_set_row_size(yanmo_engine_t* engine, int row_size);
int yanmo_set_full_width_punct(yanmo_engine_t* engine, int enabled);
int yanmo_get_full_width_punct(yanmo_engine_t* engine);
int yanmo_set_full_width_char(yanmo_engine_t* engine, int enabled);
int yanmo_get_full_width_char(yanmo_engine_t* engine);

// Explicit radical mode control
int yanmo_enter_radical_mode(yanmo_engine_t* engine);
int yanmo_set_radical_glyph(yanmo_engine_t* engine, const char* utf8_glyph);

#ifdef __cplusplus
}
#endif
