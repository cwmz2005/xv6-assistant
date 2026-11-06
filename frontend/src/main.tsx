import React from 'react';
import {createRoot} from 'react-dom/client';
import App from './App';
import 'antd/dist/reset.css';
import 'highlight.js/styles/github.css';
createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>);
