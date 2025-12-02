#!/bin/bash
module load compilers/cuda/12.4 cudnn/8.9.5.29_cuda12.x  compilers/gcc/13.2.0 cmake/3.26.3 miniforge3
export LD_PRELOAD=/home/bingxing2/apps/compilers/gcc/13.2.0/lib64/libstdc++.so.6
source activate LLaMA-Factory
# 使用 llamafactory-cli 来启动训练
llamafactory-cli version
llamafactory-cli train examples/train_full/qwen2_5_7b.yaml

