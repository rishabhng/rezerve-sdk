"""Rezerve: Consumption reporting extrinsic.

Validators call report_consumption after verifying that a miner performed
real AI compute for a paying consumer. This accumulates into SubnetConsumption
and MinerConsumption storage, driving the consumption-based emission allocation.
"""
from __future__ import annotations

from typing import Optional

from bittensor.core.types import SubnetMixin


async def report_consumption_extrinsic(
    subtensor,
    wallet,
    netuid: int,
    miner_uid: int,
    compute_units: int,
    consumer_payment: int,
    quality_score: int,
    output_hash: str = "0x" + "00" * 32,
    wait_for_inclusion: bool = True,
    wait_for_finalization: bool = False,
) -> bool:
    """Report verified AI consumption for a subnet.

    This extrinsic is called by validators after verifying that:
    1. A miner performed real compute (verified via RepOps hash)
    2. A consumer paid for the service
    3. The output meets quality thresholds

    Args:
        subtensor: The subtensor instance.
        wallet: The validator's wallet.
        netuid: The subnet ID.
        miner_uid: The UID of the miner within the subnet.
        compute_units: Number of verified compute units performed.
        consumer_payment: Amount paid by the consumer (in rao).
        quality_score: Quality score (0-10000, where 10000 = 100%).
        output_hash: RepOps deterministic hash of the inference output (32 bytes hex).
        wait_for_inclusion: Wait for the extrinsic to be included in a block.
        wait_for_finalization: Wait for the extrinsic to be finalized.

    Returns:
        True if the extrinsic was successful, False otherwise.
    """
    # Convert output_hash to bytes
    if output_hash.startswith("0x"):
        hash_bytes = bytes.fromhex(output_hash[2:])
    else:
        hash_bytes = bytes.fromhex(output_hash)

    # Ensure hash is 32 bytes
    hash_bytes = hash_bytes.ljust(32, b"\x00")[:32]

    call = subtensor.substrate.compose_call(
        call_module="SubtensorModule",
        call_function="report_consumption",
        call_params={
            "netuid": netuid,
            "miner_uid": miner_uid,
            "compute_units": compute_units,
            "consumer_payment": consumer_payment,
            "quality_score": quality_score,
            "output_hash": f"0x{hash_bytes.hex()}",
        },
    )

    extrinsic = subtensor.substrate.create_signed_extrinsic(
        call=call,
        keypair=wallet.hotkey,
    )

    response = subtensor.substrate.submit_extrinsic(
        extrinsic,
        wait_for_inclusion=wait_for_inclusion,
        wait_for_finalization=wait_for_finalization,
    )

    if wait_for_inclusion or wait_for_finalization:
        response.process_events()
        if response.is_success:
            return True
        else:
            raise Exception(f"report_consumption failed: {response.error_message}")

    return True


def get_subnet_consumption(subtensor, netuid: int) -> int:
    """Query the current consumption for a subnet.

    Args:
        subtensor: The subtensor instance.
        netuid: The subnet ID.

    Returns:
        Total verified consumption units for the subnet this epoch.
    """
    result = subtensor.substrate.query(
        module="SubtensorModule",
        storage_function="SubnetConsumption",
        params=[netuid],
    )
    return int(result.value) if result else 0


def get_miner_consumption(subtensor, netuid: int, uid: int) -> int:
    """Query the current consumption for a specific miner.

    Args:
        subtensor: The subtensor instance.
        netuid: The subnet ID.
        uid: The miner's UID within the subnet.

    Returns:
        Total verified consumption units for the miner this epoch.
    """
    result = subtensor.substrate.query(
        module="SubtensorModule",
        storage_function="MinerConsumption",
        params=[netuid, uid],
    )
    return int(result.value) if result else 0


def get_subnet_quality_score(subtensor, netuid: int) -> int:
    """Query the current quality score for a subnet.

    Args:
        subtensor: The subtensor instance.
        netuid: The subnet ID.

    Returns:
        Quality consensus score (0-10000).
    """
    result = subtensor.substrate.query(
        module="SubtensorModule",
        storage_function="SubnetQualityScore",
        params=[netuid],
    )
    return int(result.value) if result else 0


def get_bootstrap_speculative_weight(subtensor) -> int:
    """Query the current bootstrap speculative weight.

    Returns:
        Current speculative emission weight (0-10000, where 10000 = 100%).
        Decays from 8000 (80%) toward 500 (5%) over time.
    """
    result = subtensor.substrate.query(
        module="SubtensorModule",
        storage_function="BootstrapSpeculativeWeight",
    )
    return int(result.value) if result else 8000
