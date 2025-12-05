# Testing parameters for survey development

TEST_PARAMS = {
    "first_question": "I am interested in learning more about why you currently do not own any stocks or stock mutual funds. Can you help me understand the main factors or reasons why you are not participating in the stock market?",
    "closing_questions": [
			"As we conclude our discussion, are there any perspectives or information you feel we haven't addressed that you'd like to share?",
			"Reflecting on our conversation, what would you identify as the main reason you're not participating in the stock market?"
		],
    "end_of_interview_message" : "Thank you for sharing your insights and experiences today. Your input is invaluable to our research. Please proceed to the next page.---END---",
    "pre_gen_transitions" : True,
    "transition_llm": {
        "prompt": """
        
        CONTEXT: You're an AI proficient in conducting qualitative interviews for academic research. You're guiding a semi-structured qualitative interview about the interviewee's reasons for not investing in the stock market.

        Previous topic: {previous_topic}
        Next topic: {next_topic}

        TASK: Introducing the Next Interview Topic from the interview plan by asking a transition question.

				GUIDELINES:
				1. Open-endedness: Always craft open-ended questions ("how", "what", "why") that allow detailed and authentic responses without limiting the interviewee to  "yes" or "no" answers.
				2. Natural transition: To make the transition to a new topic feel more natural and less abrupt, you may use elements from the Current Conversation and Previous Conversation Summary to provide context and a bridge from what has been discussed to what will be covered next.
				3. Clarity: Your transition question should clearly and effectively introduce the new interview topic.

				YOUR RESPONSE: Please provide the most suitable next transition question in the interview, without any other discussion, context, or remarks.""",
        "model": "gpt-4o-mini",
        "model_provider": "openai",
        "kwargs": {
            "temperature": 0.7,
            "max_tokens": 100
        }
    },
    "prompter_llm": {
        "prompt": """
				CONTEXT: You're an AI proficient in conducting qualitative interviews for academic research. You conduct a qualitative interview with the goal of learning the interviewee's reasons for not investing in the stock market.

				TASK: Your task is to formulate the next probing question for the Current Conversation. The question should align with the Current Interview Topic, helping us to better understand and systematically explore why the interviewee is not participating in the stock market.

				GENERAL GUIDELINES:
				1. Open-endedness: Always craft open-ended questions ("how", "what", "why") that allow detailed and authentic responses without limiting the interviewee to  "yes" or "no" answers.
				2. Neutrality: Use questions that are unbiased and don't lead the interviewee towards a particular answer. Don't judge or comment on what was said. It's also crucial not to offer any financial advice.
				3. Respect: Approach sensitive and personal topics with care. If the interviewee signals discomfort, respect their boundaries and move on.
				4. Relevance: Prioritize themes central to the interviewee's stock market non-participation. Don't ask for overly specific examples, details, or experiences that are unlikely to reveal new insights.
				5. Focus: Generally, avoid recaps. However, if revisiting earlier points, provide a concise reference for context. Ensure your probing question targets only one theme or aspect.

				PROBING GUIDELINES:
				1. Depth: Initial responses are often at a "surface" level (brief, generic, or lacking personal reflection). Follow up on promising themes hinting at depth and alignment with the research objective, exploring the interviewee's reasons, motivations, opinions, and beliefs. 
				2. Clarity: If you encounter ambiguous language, contradictory statements, or novel concepts, employ clarification questions.
				3. Flexibility: Follow the interviewee's lead, but gently redirect if needed. Actively listen to what is said and sense what might remain unsaid but is worth exploring. Explore nuances when they emerge; if responses are repetitive or remain on the surface, pivot to areas not yet covered in depth.

				YOUR RESPONSE: Please provide the most suitable next probing question in the interview, without any other discussion, context, or remarks. The current topic is {current_topic}
			""",
        "model": "gpt-4o",
        "model_provider": "openai",
        "kwargs": {
            "temperature": 0.7,
            "max_tokens": 200
        }
    }, 
    "interview_plan": [
			{
				"topic":"Explore the reasons behind the interviewee's choice to avoid the stock market.",
				"length":2
			},
			{
				"topic":"Delve into the perceived barriers or challenges preventing them from participating in the stock market.",
				"length":2
			},
			{
				"topic":"Explore a 'what if' scenario where the interviewee invest in the stock market. What would they do? What would it take to thrive? Probing questions should explore the hypothetical scenario.",
				"length":2
			},
			{
				"topic":"Prove for conditions or changes needed for the interviewee to consider investing in the stock market.",
				"length":2
			}]
}

TEST_PARAMS_VERBOSE = {
    "first_question": "Når du tenker på Baker Brun, hva er det første du tenker på?",
    "closing_questions": [],
    "end_of_interview_message" : "Takk for at du delte innsiktene og erfaringene dine i dag. Tilbakemeldingen din er verdifull for oss. Vennligst gå videre til neste side.---END---",
    "pre_gen_transitions" : True,
    "transition_llm": {
        "prompt": """
        
        KONTEKST: Du er en AI som er dyktig på å gjennomføre kvalitative intervjuer for forskning. Du leder et semi-strukturert kvalitativt intervju om kundens syn på kvaliteten på Baker Bruns produkter.

        
        INNDATA: 
        Neste itervjutmea: {next_topic}

        OPPGAVE: Introduser Neste intervjutema fra intervjuplanen ved å stille et overgangsspørsmål.

		RETNINGSLINJER:
		1. Åpenhet: Lag alltid åpne spørsmål ("hvordan", "hva", "hvorfor") som tillater detaljerte og autentiske svar uten å begrense intervjupersonen til "ja" eller "nei" svar.
		2. Naturlig overgang: For å gjøre overgangen til et nytt tema mer naturlig og mindre brå, kan du bruke elementer fra Nåværende samtale og Tidligere samtaleoppsummering for å gi kontekst og en bro fra det som har blitt diskutert til det som skal dekkes neste gang.
		3. Klarhet: Overgangsspørsmålet ditt skal tydelig og effektivt introdusere det nye intervjutemaet.

		DITT SVAR: Vennligst gi det mest passende neste overgangsspørsmålet i intervjuet, uten annen diskusjon, kontekst eller merknader.""",
        "model": "gpt-4o",
        "model_provider": "openai",
        "kwargs": {
            "temperature": 0.7,
            "max_tokens": 300
        }
    },
    "prompter_llm": {
        "prompt": """
				KKONTEKST: Du er en AI som er dyktig på å gjennomføre kvalitative intervjuer for forskning. Du gjennomfører et kvalitativt intervju med mål om å lære kundens syn på kvaliteten på Baker Bruns produkter.

				OPPGAVE: Din oppgave er å formulere det neste utforskende spørsmålet for Nåværende samtale. Spørsmålet skal være i tråd med Nåværende intervjutema, og hjelpe oss med å bedre forstå og systematisk utforske kundens syn på Baker Bruns produktkvalitet.

				GENERELLE RETNINGSLINJER:
				1. Åpenhet: Lag alltid åpne spørsmål ("hvordan", "hva", "hvorfor") som tillater detaljerte og autentiske svar uten å begrense intervjupersonen til "ja" eller "nei" svar.
				2. Nøytralitet: Bruk spørsmål som er objektive og ikke leder intervjupersonen mot et bestemt svar. Ikke døm eller kommenter det som ble sagt.
				3. Respekt: Nærm deg sensitive og personlige temaer med forsiktighet. Hvis intervjupersonen signaliserer ubehag, respekter deres grenser og gå videre.
				4. Relevans: Prioriter temaer som er sentrale for kundens syn på Baker Bruns produktkvalitet. Ikke spør om altfor spesifikke eksempler, detaljer eller erfaringer som neppe vil avsløre nye innsikter.
				5. Fokus: Generelt, unngå oppsummeringer. Hvis du må besøke tidligere punkter, gi en kortfattet referanse for kontekst. Sørg for at ditt utforskende spørsmål retter seg kun mot ett tema eller aspekt.

				UTFORSKENDE RETNINGSLINJER:
				1. Dybde: Innledende svar er ofte på et "overfladenivå" (korte, generiske eller mangler personlig refleksjon). Følg opp lovende temaer som antyder dybde og samsvar med forskningsobjektivet, og utforsk intervjupersonens meninger, motivasjoner, synspunkter og tro.
				2. Klarhet: Hvis du møter tvetydig språk, motstridende utsagn eller nye konsepter, bruk avklarende spørsmål.
				3. Fleksibilitet: Følg intervjupersonens ledelse, men omdiriger forsiktig om nødvendig. Lytt aktivt til det som blir sagt og føl hva som kan forbli usagt, men er verdt å utforske. Utforsk nyanser når de dukker opp; hvis svarene er repeterende eller forblir på overflaten, sving til områder som ennå ikke er dekket i dybden.

				DITT SVAR: Vennligst gi det mest passende neste utforskende spørsmålet i intervjuet, uten annen diskusjon, kontekst eller merknader. Det nåværende intervjutemeat du skal utforske er {current_topic}
			""",
        "model": "gpt-4o",
        "model_provider": "openai",
        "kwargs": {
            "temperature": 0.7,
            "max_tokens": 200
        }
    }, 
    "interview_plan": [
			{
			"topic": "Åpningsassosiasjon — hva som popper opp og hvorfor. Dekning: identifiser første mentale bilde (produkt/sted/situasjon/følelse), utløsende erfaring, valens (positiv/nøytral/negativ) og ett ferskt eksempel for å jorde resten. Start f.eks. med: Når du tenker på Baker Brun, hva er det første du tenker på? Se an samtalen; la deg f.eks. inspirere av disse mulige spørsmålene: 1) Sist du var innom: hva kjøpte du og hvorfor ble det Baker Brun? 2) Hvilken anledning forbinder du oftest med Baker Brun, og hvorfor passer det da?",
			"length": 3
			},
			{
			"topic": "Konkurrent-sammenligning — PoPs (likheter) og PoDs (forskjeller). Dekning: få frem reelle alternativer deltakeren faktisk bruker (2–3), og identifiser 1–2 viktigste likheter og 1–2 tydelige forskjeller som avgjør valg i konkrete situasjoner. Forankre i to ferske hendelser: ett kjøp hos Baker Brun og ett hos nærmeste konkurrent. Start f.eks. med: Hvilke to–tre alternativer velger du oftest i samme situasjoner? Se an samtalen; la deg f.eks. inspirere av disse spørsmålene: 1) Tenk på sist du valgte Baker Brun og sist du valgte [konkurrent]: hva var likt, og hva var én ting som avgjorde valget? 2) Fullfør setningen: Jeg velger Baker Brun når ____, men [konkurrent] når ____. 3) Hva gjør Baker Brun bedre enn andre (PoD), og hva er bare på nivå (PoP)? Om dette dekkes spontant, anerkjenn og gå videre uten repetisjon.",
			"length": 7
			},
			{
			"topic": "Kundeprogram — kjennskap, bruk, verdi og friksjon. Dekning: avklar kjennskap/bruk; hent ett ferskt eksempel; identifiser én tydelig verdidriver og én hovedbarriere; hva mangler for å øke bruken. Start f.eks. med: Kjenner du til eller bruker du kundeprogrammet til Baker Brun? Se an samtalen; la deg f.eks. inspirere av disse mulige spørsmålene: 1) Fortell om siste gang du (ikke) brukte programmet: hva skjedde og hva fikk du ut av det? 2) Hva er den ene fordelen som får deg til å bruke, og den ene barrieren som gjør at du dropper det? 3) Hva skulle til for at du brukte det oftere eller opplevde mer verdi? Speil kort og referer til tidligere svar for å unngå gjentakelser.",
			"length": 5
			},
			{
			"topic": "Sjef for en dag — tre konkrete grep og rask test. Dekning: be om topp tre endringer strukturert som problem → tiltak → forventet effekt; få med en enkel testidé (hva måles, hvor, hvor lenge); avslutt med hva som må bevares. Start f.eks. med: Hvis du var sjef for Baker Brun i én dag, hva er de tre første konkrete tingene du ville endret? Se an samtalen; la deg f.eks. inspirere av disse mulige spørsmålene: 1) Hvilket tiltak ville gitt størst effekt for deg, og hvordan ville du testet det raskt? 2) Hva må forbli uendret for at Baker Brun ikke mister det som funker for deg? 3) Hva gjør en konkurrent du ville kopiert, og hvordan ville du gjort det litt bedre? Oppsummer i én setning i deltakerens ord og be om presiseringer.",
			"length": 5
			},
			{
			"topic": "Mini member-check — stemmer retningen. Dekning: bekreft forståelsen av kjerneassosiasjon, viktigste PoPs og PoDs, kundeprogram (verdi + barriere) og topp-tiltak. Start f.eks. med: Kan jeg oppsummere kort det jeg hørte, så retter du meg? Se an samtalen; la deg f.eks. inspirere av disse mulige spørsmålene: 1) Hva i oppsummeringen min mangler eller er feil, hvis du må nevne én ting? 2) Hvis du måtte velge: hva er viktigst for ditt valg mellom Baker Brun og alternativer? Juster notatene etter svar.",
			"length": 2
			},
			{
			"topic": "Avrunding — siste presisering og oppfølging. Dekning: fang opp misforståelser eller utestående punkter; få samtykke til eventuell oppfølging. Start f.eks. med: Er det noe viktig vi har oversett eller misforstått? Se an samtalen; la deg f.eks. inspirere av disse mulige spørsmålene: 1) Er det greit at vi kontakter deg hvis vi tester ett av forslagene dine? 2) Er det noe du vil legge til før vi runder av?",
			"length": 1
			}]
}