
Module("strings","$Revision: 43$",function(mod){
mod.WordNumberStringSplitter=Class(function(publ,priv,supr){
publ.__init__=function(s){
this.s=s;
};
publ.next=function(){
if(this.s.length==0){
return ;
}
var m=this.s.match(/^(\s*[0-9]+\s*)/);
if(m){
this.s=this.s.slice(m[1].length);
return Number(m[1]);
}else{
m=this.s.match(/^([^0-9]+)/);
if(m){
this.s=this.s.slice(m[1].length);
return m[1].replace(" ","");
}else{
return ;
}
}
};
});
mod.naturalCompare=function(a,b){
var asplitter=new mod.WordNumberStringSplitter(a);
var bsplitter=new mod.WordNumberStringSplitter(b);
while(true){
var x=asplitter.next();
var y=bsplitter.next();
if(x<y){
return -1;
}else if(x>y){
return 1;
}else if(x==null&&y==null){
return 0;
}
}
};
mod.WritableString=Class(Array,function(publ,supr){
publ.__init__=function(value){
value=value==null?"":value;
if(value!=""){
this.write(value);
}
};
publ.write=Array.prototype.push;
publ.__str__=function(){
return this.join("");
};
publ.__repr__=function(){
return repr(this.join(""));
};
});
mod.templateCodeStartDelimiter="<?";
mod.templateCodeEndDelimiter="?>";
String.prototype.exec=function(locals,codeStartDelimiter,codeEndDelimiter){
codeStartDelimiter=codeStartDelimiter==null?mod.templateCodeStartDelimiter:codeStartDelimiter;
codeEndDelimiter=codeEndDelimiter==null?mod.templateCodeEndDelimiter:codeEndDelimiter;
var s=this+"";
var code=[];
var p,text;
while(s.length>0){
var p=s.indexOf(codeStartDelimiter);
if(p>=0){
text=s.slice(0,p);
code.push(';out.write("'+text.replace(/\\/g,"\\\\").replace(/\"/g,"\\\"").replace(/\n/g,"\\n").replace(/\r/g,"\\r")+'");');
s=s.slice(p+codeStartDelimiter.length);
p=s.indexOf(codeEndDelimiter);
if(p>=0){
text=s.slice(0,p);
s=s.slice(p+codeEndDelimiter.length);
if(text.slice(0,1)=="="){
code.push(';out.write('+text.slice(1)+');');
}else{
code.push(text);
}
}else{
throw mod.Exception("No code end dilimiter: '%s' found".format(codeEndDelimiter));
}
}else{
code.push(';out.write("'+s.replace(/\\/g,"\\\\").replace(/\"/g,"\\\"").replace(/\n/g,"\\n").replace(/\r/g,"\\r")+'");');
s="";
}
}
var sout=new mod.WritableString();
var params=[sout];
var paramNames=["out"];
for(var key in locals){
paramNames.push(key);
params.push(locals[key]);
}
try{
var f=new Function(paramNames.join(","),code.join(""));
}catch(e){
throw new mod.Exception("Error compiling template:\n\n%s".format(code.join("")),e);
}
f.apply(sout,params);
return str(sout);
};
});
