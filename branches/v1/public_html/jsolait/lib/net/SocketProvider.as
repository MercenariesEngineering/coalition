/*
    Copyright (c) 2004-2006 Jan-Klaas Kollhof

    This file is part of the JavaScript O Lait library(jsolait).

    jsolait is free software; you can redistribute it and/or modify
    it under the terms of the GNU Lesser General Public License as published by
    the Free Software Foundation; either version 2.1 of the License, or
    (at your option) any later version.

    This software is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public License
    along with this software; if not, write to the Free Software
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
*/
 
import flash.external.ExternalInterface;

class SocketProvider {
    
    static var app : SocketProvider;
    static var sockets = [];
        
    public function SocketProvider() {
        ExternalInterface.addCallback("newSocket", null, newSocket);
        ExternalInterface.addCallback("connect", null, connect);
        ExternalInterface.addCallback("send", null, send);
        var x:Boolean=ExternalInterface.addCallback("close", null, close);
        _root.createTextField("tf",0,0,0,100,30);
        _root.tf.text = "jsolait SocketProvider " + (x==true?'OK': 'initialization failed');
        ExternalInterface.call("imprt('net.sockets').handleFlashMessage", "", "socketProviderLoaded" );
    }
    
    public function newSocket() : String {
        var id =0;
        while(sockets['s' + id] != null){
            id ++ 
        }
        id = 's' + id;
        
        var s:XMLSocket = new XMLSocket();
        sockets[id] = s;
        
        s.onData = function(data){
            data=data.split('\r').join('\\r');
            data=data.split('\n').join('\\n');
            ExternalInterface.call("imprt('net.sockets').handleFlashMessage", id, "onData", data);
        }
        s.onConnect = function(succsess){
            ExternalInterface.call("imprt('net.sockets').handleFlashMessage", id, "onConnect", succsess);
        }
        s.onClose = function(){
            ExternalInterface.call("imprt('net.sockets').handleFlashMessage", id, "onClose");
        }
	return id;     
    }
    
    public function connect(id : String, host : String, port : String){
        sockets[id].connect(host, port);
    }
    
    public function send(id : String, data : String){
        sockets[id].send(data);
    }

    public function close(id:String){
        sockets[id].close();
        delete sockets[id];
    }
    
    // entry point
    static function main(mc) {
        app =   new SocketProvider();
    }
}

 
