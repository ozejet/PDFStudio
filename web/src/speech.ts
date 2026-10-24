export type Paragraph={page:number;index:number;text:string;items:number[]};
type TextItem={str:string;transform:number[];height:number;width?:number;hasEOL?:boolean};

/** Keep indices aligned with PDF.js TextLayer.textDivs, including empty items. */
export function paragraphGroups(raw:unknown[],page:number):Paragraph[]{
 const items=raw.filter((item):item is TextItem=>typeof (item as TextItem).str==='string');
 type Line={text:string;items:number[];x:number;y:number;height:number;end:number};
 const lines:Line[]=[];let eol=false;
 items.forEach((item,index)=>{
  if(!item.str.trim()){if(item.hasEOL)eol=true;return;}
  const x=item.transform[4],y=item.transform[5],height=Math.max(1,item.height||Math.hypot(item.transform[2],item.transform[3]));
  let line=lines[lines.length-1];
  if(!line||eol||Math.abs(y-line.y)>Math.max(height,line.height)*.45){line={text:'',items:[],x,y,height,end:x};lines.push(line);}
  const gap=x-line.end;
  line.text+=(line.text&&gap>height*.12&&!/\s$/.test(line.text)?' ':'')+item.str;
  line.items.push(index);line.end=x+(item.width||0);eol=!!item.hasEOL;
 });
 const groups:Paragraph[]=[];let previous:Line|undefined;
 for(const line of lines){
  const gap=previous?previous.y-line.y:0,height=previous?Math.max(previous.height,line.height):line.height;
  const newGroup=!previous||gap>height*1.65||gap< -height*.5||Math.abs(previous.height-line.height)>height*.25||line.x-previous.x>height*.85;
  if(newGroup)groups.push({page,index:groups.length,text:line.text.trim(),items:[...line.items]});
  else{const group=groups[groups.length-1];group.text+=' '+line.text.trim();group.items.push(...line.items);}
  previous=line;
 }
 return groups;
}

export function speechChunks(text:string,max=650):string[]{
 const chunks:string[]=[];let rest=text.trim();
 while(rest.length>max){let end=rest.lastIndexOf(' ',max);if(end<max/2)end=max;chunks.push(rest.slice(0,end));rest=rest.slice(end).trim();}
 if(rest)chunks.push(rest);return chunks;
}

type Callbacks={group:(paragraph:Paragraph|null)=>void;state:(state:'idle'|'loading'|'speaking'|'paused')=>void;error:(message:string)=>void};
/** A generation token isolates canceled utterances and pending PDF extraction. */
export class ParagraphSpeaker{
 private generation=0;private iterator:AsyncIterator<Paragraph>|null=null;private chunks:string[]=[];private paragraph:Paragraph|null=null;private paused=false;private callbacks:Callbacks|null=null;
 constructor(private synth:SpeechSynthesis,private make=(text:string)=>new SpeechSynthesisUtterance(text)){}
 start(groups:AsyncIterable<Paragraph>,voice:SpeechSynthesisVoice,rate:number,callbacks:Callbacks){
  this.stop();this.callbacks=callbacks;
  if(!voice.localService){callbacks.error('Choose an installed local voice.');return;}
  this.synth.resume();this.iterator=groups[Symbol.asyncIterator]();this.paused=false;callbacks.state('loading');
  const epoch=this.generation;let announced:Paragraph|null=null;
  const next=async()=>{
   try{
    if(epoch!==this.generation)return;
    if(!this.chunks.length){const result=await this.iterator!.next();if(epoch!==this.generation)return;if(result.done){this.stop();return;}this.paragraph=result.value;this.chunks=speechChunks(result.value.text);}
    const text=this.chunks.shift();if(!text){void next();return;}
    const utterance=this.make(text);utterance.voice=voice;utterance.lang=voice.lang;utterance.rate=rate;
    utterance.onstart=()=>{if(epoch===this.generation){if(announced!==this.paragraph){announced=this.paragraph;callbacks.group(this.paragraph);}callbacks.state(this.paused?'paused':'speaking');}};
    utterance.onend=()=>{if(epoch===this.generation)void next();};
    utterance.onerror=event=>{if(epoch!==this.generation)return;this.stop();callbacks.error(`Read Aloud stopped: ${event.error||'the local voice could not continue'}.`);};
    this.synth.speak(utterance);if(this.paused)this.synth.pause();
   }catch(error){if(epoch===this.generation){this.stop();callbacks.error((error as Error).message||'This PDF text could not be read.');}}
  };
  void next();
 }
 pause(){this.paused=true;this.synth.pause();this.callbacks?.state('paused');}
 resume(){this.paused=false;this.synth.resume();this.callbacks?.state('speaking');}
 stop(){this.generation++;this.synth.cancel();this.iterator=null;this.chunks=[];this.paragraph=null;this.paused=false;this.callbacks?.group(null);this.callbacks?.state('idle');this.callbacks=null;}
}
