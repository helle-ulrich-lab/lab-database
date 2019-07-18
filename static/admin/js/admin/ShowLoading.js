function ShowLoading(e) {
    var div = document.createElement('div');
    var img = document.createElement('img');
    img.src = '/static/admin/img/helle.gif'; //'/static/admin/img/spinner.svg';
    div.innerHTML = "</br>Wart' mal 'n Moment! ...</br></br>";
    div.style.cssText = 'margin: 0; height: 12vw; width:15vw; position: fixed; \
     top: 50%; left:50%; z-index: 5000; transform: translatey(-50%); \
     box-shadow: 0 0 0 100vmax rgba(0,0,0,.3); background-color: white; \
     border: 3px solid #417690; font-family: "Roboto"; text-align: center;';
    div.appendChild(img);
    document.body.appendChild(div);
    return true;
}