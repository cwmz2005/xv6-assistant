import {Button,Card,Space} from 'antd';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import type {Evidence,Message} from '../types';
export default function MessageCard({message,onCitation}:{message:Message;onCitation:(evidence:Evidence)=>void}){
 return <Card title={message.role==='user'?'你':'xv6'} style={{marginBottom:16}}><Markdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>{message.content}</Markdown><Space wrap>{message.citations.map(c=><Button key={c.id} onClick={()=>onCitation(c)}>{c.location.path}:{c.location.start_line}–{c.location.end_line}</Button>)}</Space></Card>;
}
