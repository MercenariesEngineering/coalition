
Module("iter","$Revision: 64 $",function(mod){
mod.Iterator=Class(function(publ,supr){
publ.next=function(){
return undefined;
};
publ.__iter__=function(){
return this;
};
publ.__iterate__=function(thisObj,cb){
var result;
thisObj=thisObj==null?this:thisObj;
var item;
while(((item=this.next())!==undefined)&&result===undefined){
if(item.__tupleResult__){
item.push(this);
result=cb.apply(thisObj,item);
}else{
result=cb.call(thisObj,item,this);
}
}
return result;
};
publ.__filter__=function(thisObj,cb){
var result=[];
thisObj=thisObj==null?this:thisObj;
var item,doKeep;
while((item=this.next())!==undefined){
if(item.__tupleResult__){
item.push(this);
doKeep=cb.apply(thisObj,item);
}else{
doKeep=cb.call(thisObj,item,this);
}
if(doKeep){
result.push(item);
}
}
return result;
};
publ.__map__=function(thisObj,cb){
var result=[];
thisObj=thisObj==null?this:thisObj;
var item,mapedItem;
while((item=this.next())!==undefined){
if(item.__tupleResult__){
item.push(this);
mapedItem=cb.apply(thisObj,item);
}else{
mapedItem=cb.call(thisObj,item,this);
}
result.push(mapedItem);
}
return result;
};
publ.__list__=function(){
var list=[];
var item;
while((item=this.next())!==undefined){
list.push(item);
}
return list;
};
publ.replace=function(item){
throw new mod.Exception("Iterator::replace() not implemented");
};
});
mod.Range=Class(mod.Iterator,function(publ,supr){
publ.__init__=function(start,end,step){
switch(arguments.length){
case 1:
this.start=0;
this.end=start;
this.step=1;
break;
case 2:
this.start=start;
this.end=end;
this.step=1;
break;
default:
this.start=start;
this.end=end;
this.step=step;
break;
}
this.current=this.start-this.step;
};
publ.next=function(){
var n=this.current+this.step;
if(n>this.end){
this.current=this.start;
return undefined;
}else{
this.current=n;
return this.current;
}
};
publ.__iterate__=function(thisObj,cb){
var result=undefined;
for(this.current+=this.step;this.current<=this.end&&result===undefined;this.current+=this.step){
result=cb.call(thisObj,this.current,this);
}
return result;
};
});
mod.range=function(start,end,step){
var r=new mod.Range(Class);
r.__init__.apply(r,arguments);
return r;
};
mod.ArrayItereator=Class(mod.Iterator,function(publ,supr){
publ.__init__=function(array){
this.array=array;
this.index=-1;
};
publ.next=function(){
this.index+=1;
if(this.index>=this.array.length){
return undefined;
}else{
return this.array[this.index];
}
};
publ.__iterate__=function(thisObj,cb){
var result=undefined;
thisObj=thisObj==null?this:thisObj;
var args=[null,this];
for(this.index++;this.index<this.array.length&&result===undefined;this.index++){
result=cb.call(thisObj,this.array[this.index],this);
}
};
publ.__list__=function(){
return[].concat(this.array);
};
publ.replace=function(item1,item2){
switch(arguments.length){
case 0:
this.array.splice(this.index,1);
break;
case 1:
this.array.splice(this.index,1,item);
break;
default:
var a=[this.index,arguments.length];
for(var i=0;i<arguments.length;i++){
a.push(arguments[i]);
}
this.array.splice.apply(this.array,a);
}
this.index+=arguments.length-1;
};
});
Array.prototype.__iter__=function(){
return new mod.ArrayItereator(this);
};
mod.ObjectIterator=Class(mod.Iterator,function(publ,supr){
publ.__init__=function(obj){
this.obj=obj;
this.keys=[];
for(var n in obj){
this.keys.push(n);
}
this.index=-1;
};
publ.next=function(){
this.index+=1;
if(this.index>=this.keys.length){
return undefined;
}else{
var key=this.keys[this.index];
var rslt={key:key};
try{
rslt.value=this.obj[key];
}catch(e){
}
return rslt;
}
};
});
mod.iter=function(iterable,thisObj,cb){
var iterator;
if(iterable.__iter__!==undefined){
iterator=iterable.__iter__();
}else if(iterable.length!=null){
iterator=new mod.ArrayItereator(iterable);
}else if(iterable.constructor==Object){
iterator=new mod.ObjectIterator(iterable);
}else{
throw new mod.Exception("Iterable object does not provide __iter__ method or no Iterator found.");
}
if(arguments.length==1){
return iterator;
}else{
if(cb==null){
cb=thisObj;
thisObj=null;
}
return iterator.__iterate__(thisObj,cb);
}
};
mod.IterationCallback=function(item,iteration){};
mod.filter=function(iterable,thisObj,cb){
var iterator=mod.iter(iterable);
if(cb==null){
cb=thisObj;
thisObj=null;
}
return iterator.__filter__(thisObj,cb);
};
mod.map=function(iterable,thisObj,cb){
var iterator=mod.iter(iterable);
if(cb==null){
cb=thisObj;
thisObj=null;
}
return iterator.__map__(thisObj,cb);
};
mod.list=function(iterable){
return mod.iter(iterable).__list__();
};
mod.Zipper=Class(mod.Iterator,function(publ,priv,supr){
publ.__init__=function(iterators){
this.iterators=iterators;
};
publ.next=function(){
var r=[];
r.__tupleResult__=true;
var item;
for(var i=0;i<this.iterators.length;i++){
item=this.iterators[i].next();
if(item===undefined){
return undefined;
}else{
r.push(item);
}
}
return r;
};
});
mod.zip=function(iterable){
var iterators=[];
for(var i=0;i<arguments.length;i++){
iterators.push(mod.iter(arguments[i]));
}
return new mod.Zipper(iterators);
};
});
