#!/usr/bin/env bash
set -euo pipefail

python /shared/nas/data/m1/jiateng5/Mini_Word/generate_video_with_sound/make_videos_with_sound.py \
  --input-dir /shared/nas/data/m1/jiateng5/Mini_Word/inference/text_to_image_output/evaluate_data_combination2,3,4_inference_results \
  --json-path /shared/nas/data/m1/jiateng5/Mini_Word/inference/results_text/evaluate_data_combination2,3,4_inference_results.json \
  --output-dir /shared/nas/data/m1/jiateng5/Mini_Word/video_generate_with_sound \
  --fps 2.0 --ext avi --tts gtts --overwrite

echo "[done] Videos with sound are under /shared/nas/data/m1/jiateng5/Mini_Word/video_generate_with_sound"


