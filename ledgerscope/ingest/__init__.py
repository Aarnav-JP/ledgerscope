"""Ingestion module — broker CSV parsers."""

from ledgerscope.ingest.base import BrokerParser
from ledgerscope.ingest.zerodha import ZerodhaParser
from ledgerscope.ingest.robinhood import RobinhoodParser
from ledgerscope.ingest.ibkr import IBKRParser

PARSERS = {
    "zerodha": ZerodhaParser,
    "robinhood": RobinhoodParser,
    "ibkr": IBKRParser,
}


def get_parser(broker_name: str) -> BrokerParser:
    """Factory function to get a broker parser by name."""
    broker_name = broker_name.lower()
    if broker_name not in PARSERS:
        raise ValueError(
            f"Unknown broker: {broker_name}. "
            f"Supported brokers: {', '.join(PARSERS.keys())}"
        )
    return PARSERS[broker_name]()
