// Funzione per caricare i componenti condivisi
function loadComponent(elementId, filePath) {
    fetch(filePath)
        .then(response => response.text())
        .then(data => {
            document.getElementById(elementId).innerHTML = data;
        })
        .catch(error => console.error('Errore nel caricamento di ' + filePath, error));
}

// Carica navbar e sidebar quando la pagina è pronta
document.addEventListener('DOMContentLoaded', function() {
    loadComponent('navbar-container', '/static/components/navbar.html');
    loadComponent('sidebar-container', '/static/components/sidebar.html');
});