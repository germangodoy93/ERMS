from enum import StrEnum


class ConsentPurpose(StrEnum):
    DATA_PROCESSING = "DATA_PROCESSING"  # Required to register a customer
    PHOTOS = "PHOTOS"  # Photographs of the device (Sprint 3)
    DIAGNOSTIC_AGENT = "DIAGNOSTIC_AGENT"  # Running the diagnostic agent (Sprint 4)


class ConsentChannel(StrEnum):
    SCREEN = "SCREEN"  # Accepted by the customer on screen at reception
    PAPER = "PAPER"  # Signed on paper
    VERBAL = "VERBAL"  # Given verbally (e.g. by phone); weaker evidence
