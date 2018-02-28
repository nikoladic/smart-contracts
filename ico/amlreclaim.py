"""AML token reclaim scripting before the token release.

This code is separated from the main script to make it more testable.
"""

import csv
import logging
from collections import namedtuple
from typing import List

from ico.utils import validate_ethereum_address, check_succesful_tx
from web3.contract import Contract


logger = logging.getLogger(__name__)

#: A parsed CSV input entry
Entry = namedtuple("Entry", ("address", "label"))


def reclaim_address(token: Contract, owner: str, entry: Entry) -> int:
    """Reclsaim tokens for a single participant.

    :param token: Token contract we reclaim
    :param owner: Token owner account
    :param address: Etherereum address
    :param label: User notification label regarding this address
    :return: 1 on reclaim, 0 on skip
    """

    # Make sure we are not fed bad input, raises
    validate_ethereum_address(entry.address)

    if token.call().balanceOf(entry.address) == 0:
        logger.info("%s: looks like already reclaimed %s", entry.address, entry.label)
        return 0

    txid = token.transact({"from": owner}).transferToOwner(entry.address)
    logger.info("%s: reclaiming %s in txid %s", entry.address, entry.label, txid)

    check_succesful_tx(token.web3, txid)

    return 1


def reclaim_all(token: Contract, owner: str, reclaim_list: List[Entry]) -> int:
    """Reclaim all tokens from the given input sheet."""

    total_reclaimed = 0

    for entry in reclaim_list:
        total_reclaimed += reclaim_address(token, owner, entry)

    return total_reclaimed


def prepare_csv(stream, address_key, label_key) -> List[Entry]:
    """Processa CSV reclaim file.

    :param token: Token contract
    :param owner: ETH account set as the owner of the token
    :param stream: File stream for CSV
    :param address_key: Column holding ETH address in the CSV
    :param label_key: Column holding human readable description of the address in CSV
    :return: Number of total reclaims performed
    """

    reader = csv.DictReader(stream)
    rows = [row for row in reader]
    output_rows = []

    # Prevalidate addresses
    # Here we do it inline and make skip addresses that are not valid.
    for idx, row in enumerate(rows):
        addr = row[address_key].strip()
        label = row[label_key].strip()
        try:
            if addr:
                validate_ethereum_address(addr)
        except ValueError as e:
            logger.error("Invalid Ethereum address on row:", idx + 1, "address:", addr, "reason:", str(e), "external_id:",
                  row[label_key])
            continue

        output_row = Entry(address=addr, label=label)
        output_rows.append(output_row)

    return output_rows


def count_tokens_to_reclaim(token, rows: List[Entry]):
    """Count how many tokens are on user balances to reclaim."""

    total = 0

    for entry in rows:
        total += token.call().balanceOf(entry.address)

    return total
