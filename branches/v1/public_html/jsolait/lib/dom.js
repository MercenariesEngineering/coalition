
Module("dom","$Revision: 62 $",function(mod){
var sets=imprt("sets");
mod.Event=Class(function(publ,supr){
publ.__init__=function(type,target){
this.type=type;
this.target=target;
};
publ.type=null;
publ.target=null;
});
mod.EventTarget=Class(function(publ,supr){
publ.__init__=function(){
this.eventListeners={};
};
publ.dispatchEvent=function(evt){
if(this.eventListeners[evt.type]){
var l=this.eventListeners[evt.type].items;
for(var h in l){
if(typeof l=='function'){
l(evt);
}else{
l[h].handleEvent(evt);
}
}
}
};
publ.addEventListener=function(evtType,listener,useCapture){
if(this.eventListeners[evtType]===undefined){
this.eventListeners[evtType]=new sets.Set();
}
id(listener,true);
this.eventListeners[evtType].add(listener);
};
publ.removeEventListener=function(evtType,listener,useCapture){
if(this.eventListeners[evtType]){
this.eventListeners[evtType].discard(listener);
}
};
});
mod.EventListener=Class(function(publ){
publ.handleEvent=function(evt){
if(this['handleEvent_'+evt.type]){
this['handleEvent_'+evt.type](evt);
}
};
});
mod.EventListenerTarget=Class(mod.EventTarget,mod.EventListener,function(publ,supr){
});
});
