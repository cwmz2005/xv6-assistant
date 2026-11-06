export type Evidence={id:string;text:string;location:{path:string;start_line:number;end_line:number}};
export type Message={role:string;content:string;citations:Evidence[]};
