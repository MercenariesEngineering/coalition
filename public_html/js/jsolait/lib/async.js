Module("async","0.0.1",function(mod){
mod.Task=Class(function(publ,priv,supr){
publ.queue;
publ.timeToRun=10;
publ.__init__=function(){
this.queue=[];
for(var i=0;i<arguments.length;i++){
this.queue.push(arguments[i]);
}
};
publ.start=function(){
mod.appendTask(this);
};
publ.run=function(maxTimeToRun){
var startTime=(new Date()).getTime();
while(this.queue.length>0){
this.queue.shift().call(null);
if((new Date()).getTime()-startTime>=maxTimeToRun){
mod.appendTask(this);
break;
}
}
};
publ.insertSubtasks=function(){
for(var i=arguments.length-1;i>=0;i--){
this.queue.unshift(arguments[i]);
}
};
});
mod.tasks=[];
mod.appendTask=function(t){
mod.tasks.push(t);
};
mod.currentTask=null;
mod.runTasks=function(){
while(mod.tasks.length>0&&mod.currentTask==null){
mod.currentTask=mod.tasks.shift();
mod.currentTask.run(mod.currentTask.timeToRun);
mod.currentTask=null;
if(typeof(setTimeout)!='undefined'){
setTimeout('imprt("async").runTasks()',0);
break;
}
}
};
mod.insertSubtasks=function(t){
mod.currentTask.insertSubtasks.apply(mod.currentTask,arguments);
};
mod.IterTask=Class(function(publ,priv,supr){
publ.__init__=function(t){
this.t=t;
this.p=0;
};
publ.step=function(){
if((this.p++)<100){
mod.insertSubtasks(this.t,bind(this,this.step));
}
};
});
var iter=function(t){
var i=new mod.IterTask(t);
return mod.insertSubtasks(bind(i,i.step));
};var seq=function(){
return mod.insertSubtasks.apply(mod,arguments);
};
var runTask=function(f){
var x=(new mod.Task(f)).start();
return mod.runTasks();
};
mod.__main__=function(){
var i=0;
var k=0;
var t1=new mod.Task(function(){
print("sdfasdfasdfasdfasdfasdfasdfasdfasdfasd");
iter(function(){
print('a',i++);
iter(function(){
for(var i=0;i<1000;i++){
}
});
});
});
var t2=new mod.Task(function(){
seq(function(){
iter(function(){
print('b',k++);
iter(function(){
});
});
},function(){
print("done ..................... b");
});
});
runTask(function(){
t1.start();
t2.start();
});
};
});
