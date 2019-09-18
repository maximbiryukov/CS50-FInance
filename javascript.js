function ajax_request(argument)
{
    var aj = new XMLHttpRequest;
    aj.onreadystate = function ()
    {
        aj.readyState == 4 && aj.status == 200
        
    }
    aj.open("GET", /* url */, true)
    aj.send()
}
    