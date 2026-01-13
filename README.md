Documentation



Présentation

Ce projet consiste à créer un site vitrine qui présente des films et des séries, accompagné d’un chatbot capable de répondre aux utilisateurs en langage naturel. L’idée est de mettre en place un site simple et intuitif, et d’y intégrer un modèle d’intelligence artificielle qui fonctionne entièrement en local. 
Pour y arriver, le site repose sur deux parties : un frontend en HTML, CSS et JavaScript, qui correspond à l’interface visible et avec laquelle l’utilisateur interagit, et un backend en Python et JS, qui s’occupe de traiter les demandes, de communiquer avec le modèle IA et de gérer la logique du chatbot. Le modèle que nous avons utilisé est le QWEN 3:4B. Il est open-source et intégré à Ollama, ce qui permet de charger et d’exécuter le modèle directement sur nos ordinateurs. 
Dans le cadre du projet, nous avons aussi dû simuler un MCP (Model Context Protocol). Cette partie a servi à organiser comment le chatbot utilise ses outils et comment le backend gère les échanges entre le modèle, le site et les données récupérées. 
Finalement, ce projet nous a permis de mettre en place un prototype fonctionnel qui montre comment un site vitrine, un backend en Python et JS et un modèle IA local peuvent travailler ensemble. 

Architecture globale
Frontend

Le front-end correspond à la partie visible du site, celle que l’utilisateur utilise directement. Pour ce projet, plusieurs pages ont été réalisées en utilisant HTML, CSS et Javascript. Nous avons ainsi créé : une page d’accueil, une page ‘films’, une page ‘séries’, une page dédiée au chatbot et une page “À propos”. Toutes partagent la même mise en page et avec une navigation commune. Le site est également responsive, avec les rubriques de la barre de navigation se transformant en menu à dérouler pour les petits écrans.
Les pages Films et Séries sont générées dynamiquement. Au lieu d’ajouter les œuvres une par une dans le code HTML, leur contenu est créé en JavaScript à partir des données récupérées grâce au scraping. Les titres, les images et les descriptions sont donc extraits directement depuis les sites sources, puis intégrés automatiquement à notre site, ce qui rend le processus plus rapide, et l’affichage plus propre.
Ces pages proposent aussi plusieurs façons de filtrer ou de chercher des titres. L’utilisateur peut taper du texte dans une barre de recherche, choisir un genre ou une année, ou encore trier les résultats dans l’ordre alphabétique qu’il souhaite. À chaque action, le site envoie une requête à l’API du backend, qui renvoie les données correspondantes sous forme de JSON. Le JavaScript s’occupe ensuite de transformer ces données en actions visibles à l’écran.
Grâce à cette communication entre le front et le backend, les pages ‘films’ et ‘séries’ peuvent afficher une vingtaine de titres automatiquement, et être modifiées en fonction des filtres choisis. Cette partie du site est maintenant en place et fonctionne correctement, en attendant l’ajout final du chatbot IA.


Backend 

Le backend joue un rôle central du site entre l’interface utilisateur en pilotant les flux, la logique et les interactions avec les outils externes et l’agent IA.
Le langage utilisé est python et permet de gérer les routes, les sessions, la communication avec les données et le traitement des requêtes.
Le serveur FastAPI est une framework utilisé pour créer une API et fournit les points d’entrée du système. Ce serveur est implémenté dans (backend/main.py). Ce fichier met en place une API backend avec un catalogue de films et/ou séries consultable depuis le front (recherche + filtres). Des filtres disponibles (genres, années) selon le type film ou série. Un chatbot de recommandation qui utilise une IA locale via Ollama pour répondre à l’utilisateur. 
Une configuration CORS a été mise en place pour permettre au site web d’interroger l’API sans restriction technique lors des requêtes de chaque session.
Ce serveur constitue le point d’entrée principal du système. Il reçoit l’ensemble des requêtes émises par le front-end et gère les sessions afin de maintenir un contexte conversationnel cohérent. Il expose également les endpoints nécessaires au fonctionnement du MCP, incluant la consultation de la liste des outils disponibles et l’exécution contrôlée des tools. Les échanges sont standardisés au format JSON.
L’agent IA est regroupé dans le dossier backend/agent/. 
Le fichier orchestrator.py est responsable du raisonnement et du routage des requêtes. Il analyse le message utilisateur afin d’identifier l’intention principale, par exemple une demande de recommandation de film ou série. En fonction de cette analyse, il décide s’il est nécessaire de faire appel à un ou plusieurs outils, déclenche ces appels via la couche MCP, intègre les résultats obtenus dans le contexte, puis sollicite le modèle de langage (LLM) pour générer la réponse finale.
Les règles de comportement du chatbot sont définies dans le fichier prompts.py afin de contraindre le modèle dans l’univers des films et séries. La séparation entre un prompt de routage (détermination de l’intention) et un prompt de génération de réponse améliore la cohérence globale et limite les réponses hors sujet du bot.
La gestion du contexte conversationnel est assurée par le fichier memory.py. Celui-ci conserve l’historique des messages pour chaque session utilisateur et enregistre certaines préférences, telles que les genres appréciés.
Enfin, le fichier ollama_client.py encapsule les appels au modèle de langage local via Ollama. Il uniformise les requêtes envoyées au LLM, gère les paramètres du modèle et les contraintes de communication, et renvoie uniquement le contenu nécessaire à la génération de la réponse finale.


Serveur MCP et Tooling

Le Model Context Protocol (MCP) est un protocole bidirectionnel et qui standardise la manière dont l’application fournira le contexte au LLM. La construction du serveur MCP est en langage python pour faciliter la connexion fluides des grands modèles d’IA avec des sources de données externes et des outils via une interface. 
Son rôle principal permet l’enregistrement des outils disponibles, la description des outils à l’IA, l’exécution contrôlée des outils, le retour des résultats au format JSON.

Les tools, situés dans le dossier backend/tools/, correspondent aux actions concrètes réalisées par le système pour accéder à des données réelles. Leur rôle est strictement limité à la récupération et à la structuration des informations.
Le fichier scrape_search.py permet de rechercher des films ou des séries à partir de critères. Il retourne une liste de résultats comprenant des champs standardisés comme le titre, l’année, les genres.
Le fichier scrape_details.py est dédié à la récupération d’informations détaillées sur un titre précis. Il extrait notamment le synopsis, les genres, la durée ou le nombre de saisons, l’année de sortie ainsi que l’URL source. Les données sont renvoyées sous la forme d’un objet JSON représentant une fiche complète. Le scraping se fait avec httpx et BeautifulSoup.
La logique réseau est centralisée dans le fichier http.py, qui encapsule les appels HTTP vers les sources externes. Cette approche permet d’éviter la duplication de code, de gérer les paramètres réseau et de faciliter le respect des bonnes pratiques en matière de scraping, notamment en contrôlant le débit des requêtes lors des sessions.
 
Flux de données:

Utilisateur → Message
↓
Interface Chatbot
↓
API IA
↓
Traitement de la réponse
↓
Affichage sur le site


Limites du projet et améliorations





Conclusion
