import React from 'react';
import {createRoot} from 'react-dom/client';
import App from './App';
import {ConfigProvider} from 'antd';
import zhCN from 'antd/es/locale/zh_CN';
import 'antd/dist/reset.css';
import './styles.css';
createRoot(document.getElementById('root')!).render(<React.StrictMode><ConfigProvider locale={zhCN} theme={{token:{colorPrimary:'#234c46',colorText:'#202624',colorTextSecondary:'#757c78',colorBorder:'#e4e7e4',borderRadius:10,fontFamily:'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif',controlHeight:36},components:{Button:{primaryShadow:'none',defaultShadow:'none'},Drawer:{paddingLG:28},Table:{headerBg:'#f7f8f6',headerColor:'#69736e',cellPaddingBlock:14}}}}><App/></ConfigProvider></React.StrictMode>);
