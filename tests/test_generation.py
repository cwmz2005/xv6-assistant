from types import SimpleNamespace
from backend import generation

def test_bounded_search_answers_every_tool_call_and_sanitizes_citations(monkeypatch):
    from langchain_core.messages import AIMessage,ToolMessage
    known='a'*64;unknown='b'*64
    class Model:
        def bind_tools(self,schema): return self
        def invoke(self,messages):
            if any(isinstance(m,ToolMessage) for m in messages):
                assert sum(isinstance(m,ToolMessage) for m in messages)==4
                return AIMessage(content=f'answer [{known}] [{unknown}]')
            return AIMessage(content='',tool_calls=[{'name':'knowledge_search','args':{'query':'walkaddr'},'id':str(i),'type':'tool_call'} for i in range(4)])
    monkeypatch.setattr(generation,'model',lambda:Model())
    calls=[]
    def search(query):
        calls.append(query)
        return {'results':[{'id':known,'text':'evidence','location':{}}]}
    answer,citations,logs=generation.generate('question',[],[],search_tool=search)
    assert len(calls)==1 and len(logs)==1
    assert citations[0]['id']==known
    assert unknown not in answer

def test_baseline_does_not_claim_evidence(monkeypatch):
    class Model:
        def invoke(self,messages):
            assert '当前未检索知识库' in messages[0].content
            return SimpleNamespace(content='baseline answer')
    monkeypatch.setattr(generation,'model',lambda:Model())
    assert generation.generate('question',[],[],rag=False)[1]==[]

def test_default_allows_multiple_distinct_searches(monkeypatch):
    from langchain_core.messages import AIMessage,ToolMessage
    class Model:
        def bind_tools(self,schema): return self
        def invoke(self,messages):
            count=sum(isinstance(m,ToolMessage) for m in messages)
            if count<2:
                return AIMessage(content='',tool_calls=[{'name':'knowledge_search','args':{'query':f'file-{count}'},'id':str(count),'type':'tool_call'}])
            return AIMessage(content='Evidence collected')
    monkeypatch.setattr(generation,'model',lambda:Model())
    calls=[]
    def search(query):
        calls.append(query)
        return {'results':[{'id':query,'text':query,'location':{}}]}
    _,_,logs=generation.generate('cross file question',[],[],search_tool=search)
    assert calls==['file-0','file-1'] and len(logs)==2

def test_unique_short_citation_resolves_to_real_evidence(monkeypatch):
    from langchain_core.messages import AIMessage
    cid='1234abcd'+'a'*56
    class Model:
        def invoke(self,messages): return AIMessage(content='claim [1234abcd]')
    monkeypatch.setattr(generation,'model',lambda:Model())
    answer,citations,_=generation.generate('question',[],[{'id':cid}])
    assert '['+cid+']' in answer and citations==[{'id':cid}]

def test_truncated_response_is_explicit(monkeypatch):
    from langchain_core.messages import AIMessage
    class Model:
        def invoke(self,messages):return AIMessage(content='partial',response_metadata={'finish_reason':'length'})
    monkeypatch.setattr(generation,'model',lambda:Model())
    assert '回答尚未完成' in generation.generate('question',[],[],False)[0]
