# Présentation de Coalition #
Coalition est un service qui permet de répartir différentes tâches sur les ordinateurs qui lui sont attachés. On distingue donc un serveur et des workers.\\
L’utilisateur ne se préoccupe pas de qui sont le serveur et les workers. Seul l’administrateur les utilise.

[Schéma des liens entre worker et Serveur principal]
<img src='http://coalition.googlecode.com/files/Schema.png' title='Schema' height='400'>

Coalition est composé d’un serveur principal (Gauss) et de plusieurs workers. Le schéma représente la configuration mise en place ici.<br>
<br>
<br>
<h2>Le serveur</h2>
Il est lancé par l’administrateur. Son rôle est de recevoir la liste des tâches à effectuer et de les répartir entre les différents ordinateurs (workers) susceptibles de les exécuter. Ainsi lorsqu’un utilisateur dépose une nouvelle tâche, il la soumet au serveur et ne se préoccupe pas de l’ordinateur sur laquelle elle sera effectivement exécutée.\\<br>
On peut consulter la liste des tâches par une interface web. Lorsqu'on se connecte au serveur (<a href='http://gauss:8080/'>http://gauss:8080/</a>), la page d'accueil est la suivante:<br>
<br>
<img src='http://coalition.googlecode.com/files/Screenshot.png' title='Welcome' height='400'>

<h2>Les workers</h2>
Un worker est un ordinateur qui communique avec le serveur. Lorsque le worker est inactif, il demande une tâche au serveur. Si le serveur dispose d’une tâche non attribuée, il la lui confie.\\<br>
En pratique, de plus en plus d’ordinateurs disposent de processeurs multicores, voire même de plusieurs processeurs. Dans ce cas, chaque processeur est capable d’exécuter une tâche à lui seul et on peut donc faire tourner autant de workers que de processeurs. C’est le cas sur les serveurs<br>
d’AgroParisTech (Galileo64, Aristote64, Kuiper64).<br>
<br>
<br>
<h1>Soumettre une tâche simple</h1>
Une tâche doit consister simplement en une ligne de  commandes qui sera exécutée par n’importe lequel des workers. Comme le compte d’un utilisateur est accessible depuis chacun des ordinateurs (Kuiper64, Galileo64, Aristote64) on peut accéder à n’importe lequel de ses répertoires.<br>
<br>
<h2>Exemple 1.</h2>
Je souhaite lister le contenu de mon répertoire TestCoalition. Les workers sont tous sous Linux, on doit donc utiliser la commande ls pour lister le contenu du répertoire.<br>
<blockquote>- Se connecter sur la page <a href='http://gauss:8080/'>http://gauss:8080/</a>, (ou depuis l'extérieur <a href='http://gauss.agroparistech.fr:8080/'>http://gauss.agroparistech.fr:8080/</a> )<br>
- Dans la section Title, donner un nom  à sa tâche, par exemple MaPremiereTache,<br>
- Indiquer la commande à effectuer, ici ls,<br>
- Indiquer dans quel répertoire exécuter cette commande, ici data/TestCoalition,<br>
- Laisser les autres champs libres pour le moment.<br>
<img src='http://coalition.googlecode.com/files/Screenshot2.jpg' title='2' height='400'>
- Il suffit de soumettre la tâche en cliquant sur Add job, en bas à gauche.<br>
La tâche (le job) est alors ajouté à la liste des tâches. Puisque les workers étaient disponibles, la tâche passe directement en exécution. Si on réactualise la page, on voit que le job a été effectué.</blockquote>

La commande ls liste le contenu du répertoire sur la sortie standard. Toutes ce qui est affiché sur la sortie standard se retrouve dans les logs.<br>
<br>
Si on veut sauver les logs dans un fichier plutôt que dans la sortie standard, il suffit de changer un peu la ligne de commandes et de remplacer "ls" par "ls>>monfichier.txt".