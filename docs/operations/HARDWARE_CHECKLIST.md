# Workstation Hardware Validation Checklist

This document records requirements, not a claim that the GTX 980 has been installed or validated.

## Current planning configuration

- Windows 10 Pro.
- Intel Core i7-6700K.
- 32 GB RAM.
- GTX 1660 6 GB currently available for training/evaluation.
- ASUS ROG STRIX GTX 980 DirectCU II OC 4 GB intended for resident inference.
- GTX 980 compute capability: Maxwell 5.2.
- PSU is reported as 750 W, but exact make/model, 12 V capacity, age, and native connector availability are unknown.

## Before physical installation

- [ ] Confirm exact PSU manufacturer and model.
- [ ] Confirm PSU label and 12 V rail capacity.
- [ ] Confirm native PCIe 8-pin and 6-pin connectors required by the exact card.
- [ ] Do not use SATA-to-PCIe power adapters.
- [ ] Confirm card length and case clearance.
- [ ] Confirm slot spacing and airflow with both GPUs installed.
- [ ] Confirm motherboard slot configuration and lane sharing.
- [ ] Inspect card condition, fans, heatsink, and connectors.
- [ ] Plan temperature monitoring and a safe first boot.

Do not provide unconditional installation approval until PSU, connectors, clearance, and cooling have been checked.

## After installation

- [ ] Confirm BIOS and Windows detect both GPUs.
- [ ] Record device names, IDs, driver version, memory, and compute capability.
- [ ] Confirm GTX 1660 training environment still works unchanged.
- [ ] Identify an inference backend that supports Maxwell 5.2.
- [ ] Run a small inference smoke test on GTX 980.
- [ ] Record VRAM/RAM, load time, first-token latency, tokens/sec, and temperature.
- [ ] Run a sustained stability test.
- [ ] Test model unload/reload and recovery.
- [ ] Confirm GPU selection is explicit and does not assume VRAM pooling.

## Model benchmark matrix

Test each supported combination:
- Qwen3-0.6B base.
- Qwen3-0.6B fine-tuned candidate.
- Qwen2.5-1.5B-Instruct base.
- Qwen2.5-1.5B-Instruct fine-tuned candidate.

Record backend/version, quantisation, context length, GPU, driver, model revision, adapter revision, load time, VRAM peak, system RAM peak, first-token latency, generation throughput, output quality, and failure notes.

## Important constraints

- Two GPUs do not combine their VRAM.
- Maxwell support in current ML libraries is not assumed.
- Keep the known-working GTX 1660 training environment intact.
- Do not report unsupported runtime features as available.
- Benchmarks must be reproducible and must not be fabricated.