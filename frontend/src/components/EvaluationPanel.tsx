import {useState} from 'react';
import {Alert,Button,Input,Space,Switch,Typography} from 'antd';
import {api} from '../api/client';
import EvaluationResults,{type ExperimentResult} from './EvaluationResults';
export default function EvaluationPanel(){
 const [generate,setGenerate]=useState(false);
 const [dataset,setDataset]=useState(''),[rerank,setRerank]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(''),[result,setResult]=useState<ExperimentResult>();
 async function run(){setBusy(true);setError('');try{const cases=dataset.split('\n').filter(v=>v.trim()).map(v=>JSON.parse(v));setResult(await api<ExperimentResult>('evaluation/run',{cases,include_reranker:rerank,generate_answers:generate}));}catch(e){setError(String(e));}finally{setBusy(false);}}
 function download(){const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));const link=document.createElement('a');link.href=url;link.download='retrieval-experiment.json';link.click();URL.revokeObjectURL(url);}
 return <><Typography.Title level={5}>检索消融实验</Typography.Title><Typography.Paragraph>粘贴已完成人工标注的 JSONL。比较 Dense、Hybrid 与可选重排序，此处不计算回答准确率。</Typography.Paragraph><Input.TextArea rows={8} value={dataset} onChange={e=>setDataset(e.target.value)}/><Space style={{margin:'16px 0'}}><Switch checked={generate} onChange={setGenerate} checkedChildren="LLM" unCheckedChildren="LLM"/><Switch checked={rerank} onChange={setRerank}/><Button loading={busy} disabled={!dataset.trim()} onClick={run}>运行实验</Button><Button disabled={!result} onClick={download}>导出 JSON</Button></Space>{error&&<Alert type="error" message={error}/>}{result&&<EvaluationResults result={result} onChange={setResult}/>}<pre hidden style={{whiteSpace:'pre-wrap'}}>{JSON.stringify(result,null,2)}</pre></>;
}
