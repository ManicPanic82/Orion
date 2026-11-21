# Agent Guide: Phase 15 — Hardware and Performance Validation

## Objective
Validate real model inference and sustained operation on the actual workstation, without destabilising the existing training environment.

## Prerequisites
Model Manager, runtime adapter, resource telemetry, reproducible benchmark harness.

## Hardware facts and unknowns
- Windows 10 Pro workstation.
- Intel i7-6700K, 32 GB RAM.
- GTX 1660 6 GB currently used for training/evaluation.
- ASUS ROG STRIX GTX 980 DirectCU II OC 4 GB intended for resident inference; installation not yet confirmed.
- GTX 980 is Maxwell compute capability 5.2.
- PSU make/model/connectors/capacity and case clearance must be verified before installation.
- Do not use SATA-to-PCIe power adapters.
- Two GPUs do not pool VRAM.

## Implementation instructions
1. Inventory OS, driver, GPU, device IDs, compute capability, memory, and runtime versions.
2. Validate physical installation, PSU, native PCIe connectors, clearance, and cooling before recommending operation.
3. Do not modify the known-working GTX 1660 Python/CUDA environment.
4. Identify an inference backend that explicitly supports the GTX 980/Maxwell combination; verify with actual execution.
5. Benchmark Qwen3-0.6B and Qwen2.5-1.5B-Instruct base and fine-tuned variants when compatible.
6. Record load time, VRAM, RAM, first-token latency, tokens/sec, context, quantisation, temperature, power where available, and sustained stability.
7. Run tests at short context first (e.g. 2K–4K) and increase only with evidence.
8. Separate training and resident inference scheduling; avoid GPU contention.
9. Report unsupported kernels/features honestly.
10. Save environment manifest and raw benchmark results for reproducibility.

## Forbidden shortcuts
- No unconditional GTX 980 installation approval before PSU and physical checks.
- No assumption that PyTorch/bitsandbytes/Unsloth support Maxwell.
- No VRAM pooling claims.
- No changes to existing training stack without explicit approval.
- No fabricated benchmark results.

## Acceptance tests
- Hardware inventory captured.
- Driver/runtime compatibility demonstrated.
- Real profile load and generation.
- Resource telemetry checked against independent tools.
- Sustained run and recovery tested.
- Benchmark report includes exact configuration and failures.

## Handoff
Provide hardware checklist, runtime support matrix, benchmark files, test commands, and clear go/no-go recommendations.