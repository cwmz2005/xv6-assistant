from pypdf import PdfWriter
from backend.pdf_source import pdf_chunks,pdf_report

def test_blank_pdf_does_not_fabricate_text(tmp_path):
    path=tmp_path/'blank.pdf'
    writer=PdfWriter();writer.add_blank_page(width=600,height=800)
    with path.open('wb') as f:writer.write(f)
    assert list(pdf_chunks(path))==[]
    report=pdf_report(path)
    assert report['pages']==1 and report['empty_pages']==[1]
