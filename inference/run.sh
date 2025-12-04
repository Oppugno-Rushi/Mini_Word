#!/bin/bash
# Run inference on all evaluation JSON files

cd /shared/nas/data/m1/jiateng5/Mini_Word/inference

python inference_video.py \
    --json-files \
    ../create_evaluation_data/generate_data_combination2.json \
    ../create_evaluation_data/generate_data_combination3.json \
    ../create_evaluation_data/generate_data_combination4.json

