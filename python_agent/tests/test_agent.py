from app.agent import AgenticDocumentProcessor
from app.models import DocumentProcessRequest


def test_invoice_parsing_basic():
    proc = AgenticDocumentProcessor()
    text = """
    Invoice No: INV-12345
    Date: 2024-07-15
    Vendor: Acme Corp
    Total: $1,234.56
    """
    req = DocumentProcessRequest(text=text, document_type="invoice")
    res = proc.process(req)

    assert res.status == "ok"
    fields = res.extracted_fields
    assert fields["invoice_number"].value == "INV-12345"
    assert fields["date"].value == "2024-07-15"
    assert fields["vendor_name"].value.lower().startswith("acme")
    assert fields["total_amount"].value == "1234.56"


def test_invoice_parsing_slash_date_and_parentheses_amount():
    proc = AgenticDocumentProcessor()
    text = """
    Invoice # abc-987
    Date: 7/5/2024
    Vendor: Example LLC
    Total: ($2,000.00)
    """
    req = DocumentProcessRequest(text=text, document_type="invoice")
    res = proc.process(req)

    assert res.status == "ok"
    fields = res.extracted_fields
    assert fields["invoice_number"].value == "ABC-987"
    assert fields["date"].value == "2024-07-05"
    assert fields["total_amount"].value == "2000.00"
