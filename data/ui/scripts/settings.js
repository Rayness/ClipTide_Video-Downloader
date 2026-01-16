// data/ui/scripts/settings.js

window.updateDownloadFolder = function(folder_path) {
    const el = document.getElementById('folder_path');
    if(el) el.placeholder = folder_path;
}

window.updateConvertFolder = function(folder_path) {
    const el = document.getElementById('conv_folder_path');
    if(el) el.placeholder = folder_path;
}

document.getElementById("chooseButton").addEventListener("click", function() {
    window.pywebview.api.choose_folder();
});
document.getElementById("byDefoult").addEventListener("click", function() {
    window.pywebview.api.switch_download_folder();
});
document.getElementById("openFolder").addEventListener("click", () =>{
    const folder = document.getElementById('folder_path').placeholder;
    window.pywebview.api.open_folder(folder);
});

document.getElementById("chooseButton-conv").addEventListener("click", function() {
    window.pywebview.api.choose_converter_folder();
});
document.getElementById("byDefoult-conv").addEventListener("click", function() {
    window.pywebview.api.switch_converter_folder();
});
document.getElementById("openFolder-conv").addEventListener("click", () =>{
    const folder = document.getElementById('conv_folder_path').placeholder;
    window.pywebview.api.open_folder(folder);
});

document.getElementById("update").addEventListener("click", function(){
    window.pywebview.api.launch_update();
});

document.getElementById('language').addEventListener('change', function() {
    const lang = document.getElementById('language').value || 'en';
    window.pywebview.api.switch_language(lang);
});

window.setLanguage = function(lang) {
    const select = document.getElementById("language");
    if (select) select.value = lang;
}