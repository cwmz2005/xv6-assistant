import 'highlight.js/styles/github.css';
import {Button,Space} from 'antd';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import type {Evidence,Message} from '../types';
export default function MessageCard({message,onCitation}:{message:Message;onCitation:(evidence:Evidence)=>void}){
 const content=message.content.replace(/\[([0-9a-f]{8,64})\]/g,(_,id:string)=>{const index=message.citations.findIndex(c=>c.id===id);return index>=0?`[${index+1}](#evidence-${id})`:'〔引用〕';});
 return <article className={`message ${message.role==='user'?'user':'assistant'}`}><div className="message-label">{message.role==='user'?'你':'xv6'}</div><Markdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]} components={{a:({href,children})=>{const evidence=message.citations.find(c=>href==='#evidence-'+c.id);return evidence?<button className="inline-citation" onClick={()=>onCitation(evidence)} title={evidence.location.path}>{children}</button>:<a href={href} target="_blank" rel="noreferrer">{children}</a>;}}}>{content}</Markdown><Space wrap>{message.citations.map(c=><Button className="citation-chip" size="small" key={c.id} onClick={()=>onCitation(c)}>{c.location.path}{c.location.page?` · 第 ${c.location.page} 页`:`:${c.location.start_line}–${c.location.end_line}`}</Button>)}</Space></article>;
}
