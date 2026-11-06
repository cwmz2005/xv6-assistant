import KnowledgePanel from './components/KnowledgePanel';
import {streamChat} from './api/stream';
import {useEffect,useState} from 'react';
import {Layout,Button,Input,Select,Switch,Space,Drawer,InputNumber,Alert,List,Typography} from 'antd';
import {api} from './api/client';
import type {Message} from './types';
import MessageCard from './components/MessageCard';
import EvaluationPanel from './components/EvaluationPanel';
export default function App(){
 const [sessions,setSessions]=useState<{id:string;title:string}[]>([]),[sid,setSid]=useState(''),[messages,setMessages]=useState<Message[]>([]);
 const [question,setQuestion]=useState(''),[error,setError]=useState(''),[rag,setRag]=useState(true),[rerank,setRerank]=useState(false),[strategy,setStrategy]=useState('hybrid');
 const [tools,setTools]=useState(false),[draft,setDraft]=useState('');
 const [top,setTop]=useState(5),[busy,setBusy]=useState(false),[panel,setPanel]=useState(false),[details,setDetails]=useState<unknown>();
 const refresh=()=>api<{id:string;title:string}[]>('sessions').then(setSessions);
 useEffect(()=>{refresh().catch(e=>setError(String(e)));},[]);
 async function create(){const s=await api<{id:string}>('sessions',{});setSid(s.id);setMessages([]);await refresh();return s.id;}
 async function load(id:string){setSid(id);setMessages(await api<Message[]>('sessions/'+id+'/messages'));}
 const query=()=>({query:question,strategy,rerank,top_k:top});
 async function send(){setBusy(true);try{const id=sid||await create();setDraft('');const r=await streamChat({...query(),session_id:id,rag,tools},token=>setDraft(v=>v+token));setDraft('');setMessages(v=>[...v,{role:'user',content:question,citations:[]},{role:'assistant',content:r.answer,citations:r.citations}]);setDetails(r);setQuestion('');await refresh();}catch(e){setError(String(e));}finally{setBusy(false);}}
 return <Layout style={{minHeight:'100vh'}}><Layout.Sider theme="light" width={240} style={{padding:20}}><Typography.Title level={4}>xv6 知识库</Typography.Title><Button block onClick={()=>create().catch(e=>setError(String(e)))}>新会话</Button><List dataSource={sessions} renderItem={s=><List.Item><Button type="text" onClick={()=>load(s.id).catch(e=>setError(String(e)))}>{s.title}</Button></List.Item>}/><Button onClick={()=>api('documents').then(v=>{setDetails(v);setPanel(true);}).catch(e=>setError(String(e)))}>知识库文档</Button></Layout.Sider><Layout.Content style={{padding:32,maxWidth:1100,width:'100%',margin:'auto'}}>{error&&<Alert type="error" message={error} closable onClose={()=>setError('')}/>}<section style={{minHeight:'55vh'}}>{messages.map((message,i)=><MessageCard key={i} message={message} onCitation={evidence=>{setDetails(evidence);setPanel(true);}}/>)}{draft&&<MessageCard message={{role:'assistant',content:draft,citations:[]}} onCitation={()=>{}}/>}</section><Input.TextArea rows={3} value={question} onChange={e=>setQuestion(e.target.value)} placeholder="提问 xv6"/><Space wrap style={{marginTop:16}}><Button type="primary" loading={busy} disabled={!question.trim()} onClick={send}>发送</Button><Switch checked={rag} onChange={setRag} checkedChildren="RAG" unCheckedChildren="Baseline"/><Switch checked={tools} onChange={setTools} checkedChildren="Search" unCheckedChildren="Search"/><Select value={strategy} onChange={setStrategy} options={['dense','bm25','hybrid'].map(value=>({value,label:value}))}/><Switch checked={rerank} onChange={setRerank} checkedChildren="重排序" unCheckedChildren="重排序"/><Button onClick={()=>api('search',query()).then(v=>{setDetails(v);setPanel(true);}).catch(e=>setError(String(e)))}>检索调试</Button><Button onClick={()=>setPanel(true)}>实验与高级配置</Button></Space><Drawer title="实验与证据" width={720} open={panel} onClose={()=>setPanel(false)}>Top K <InputNumber min={1} max={30} value={top} onChange={v=>setTop(v??5)}/><Typography.Paragraph>相关性分数不代表答案正确率。</Typography.Paragraph><KnowledgePanel/><EvaluationPanel/><pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{JSON.stringify(details,null,2)}</pre></Drawer></Layout.Content></Layout>;
}
