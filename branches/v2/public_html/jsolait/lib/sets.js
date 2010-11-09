
Module("sets","$Revision: 62 $",function(mod){
mod.ItemNotFoundInSet=Class(mod.Exception,function(publ,supr){
publ.set;
publ.item;
publ.__init__=function(set,item){
this.set=set;
this.item=item;
};
});
mod.Set=Class(function(publ,supr){
publ.__init__=function(elem){
this.items={};
if(arguments.length>1){
for(var i=0;i<arguments.length;i++){
this.add(arguments[i]);
}
}else if(arguments.length==1){
var elems=arguments[0];
if(elems instanceof Array){
for(var i=0;i<elems.length;i++){
this.add(elems[i]);
}
}else{
throw new mod.Exception("Expecting an Array object or multiple arguments");
}
}
};
publ.add=function(item){
this.items[id(item)]=item;
return item;
};
publ.remove=function(item){
var h=id(item);
if(this.items[h]===undefined){
throw new mod.ItemNotFoundInSet(this,item);
}else{
item=this.items[h];
delete this.items[h];
return item;
}
};
publ.discard=function(item){
var h=id(item);
item=this.items[h];
delete this.items[h];
return item;
};
publ.contains=function(item){
return(this.items[id(item)]!==undefined);
};
publ.isSubset=function(setObj){
for(var n in this.items){
if(setObj.contains(this.items[n])==false){
return false;
}
}
return true;
};
publ.isSuperset=function(setObj){
return setObj.isSubset(this);
};
publ.equals=function(setObj){
return(this.isSubset(setObj)&&setObj.isSubset(this));
};
publ.__eq__=function(setObj){
if(setObj.isSubset!==undefined){
return this.equals(setObj);
}else{
return false;
}
};
publ.union=function(setObj){
var ns=this.copy();
ns.unionUpdate(setObj);
return ns;
};
publ.intersection=function(setObj){
var ns=new mod.Set();
for(var n in this.items){
var item=this.items[n];
if(setObj.contains(item)){
ns.add(item);
}
}
return ns;
};
publ.difference=function(setObj){
var ns=new mod.Set();
for(var n in this.items){
var item=this.items[n];
if(setObj.contains(item)==false){
ns.add(item);
}
}
return ns;
};
publ.symmDifference=function(setObj){
var ns=this.difference(setObj);
return ns.unionUpdate(setObj.difference(this));
};
publ.unionUpdate=function(setObj){
for(var n in setObj.items){
this.add(setObj.items[n]);
}
return this;
};
publ.intersectionUpdate=function(setObj){
for(var n in this.items){
var item=this.items[n];
if(setObj.contains(item)==false){
this.remove(item);
}
}
return this;
};
publ.differenceUpdate=function(setObj){
for(var n in this.items){
var item=this.items[n];
if(setObj.contains(item)){
this.remove(item);
}
}
return this;
};
publ.symmDifferenceUpdate=function(setObj){
var union=setObj.difference(this);
this.differenceUpdate(setObj);
return this.unionUpdate(union);
};
publ.copy=function(){
var ns=new mod.Set();
return ns.unionUpdate(this);
};
publ.clear=function(){
this.items={};
};
publ.toArray=function(){
var a=[];
for(var n in this.items){
a.push(this.items[n]);
}
return a;
};
publ.__str__=function(){
var items=[];
for(var n in this.items){
items.push(this.items[n]);
}
return "{"+items.join(",")+"}";
};
});
});
