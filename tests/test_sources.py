from backend.sources import directory_files

def test_html_strips_scripts_and_preserves_content(tmp_path):
    (tmp_path/'lab.html').write_text('<h1>实验</h1><script>ignore()</script><pre>walkaddr()</pre>',encoding='utf-8')
    (tmp_path/'.env').write_text('secret')
    rows=list(directory_files(tmp_path))
    assert len(rows)==1
    assert '实验' in rows[0][1] and 'walkaddr()' in rows[0][1]
    assert 'ignore()' not in rows[0][1]
