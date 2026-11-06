export type Evidence={id:string;text:string;location:{path:string;start_line:number|null;end_line:number|null;page?:number;page_label?:string;section?:string}};
export type Message={role:string;content:string;citations:Evidence[]};
