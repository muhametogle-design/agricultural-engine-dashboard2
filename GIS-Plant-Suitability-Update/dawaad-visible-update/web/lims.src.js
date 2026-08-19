/* LabOps LIMS v9 — modular React source, loaded directly by lims.html */
const { useState, useMemo, useEffect } = React;
const e = React.createElement;
const { BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, Legend,
        CartesianGrid, ResponsiveContainer } = Recharts;
const SHARED_AGRI = window.AGRI_SHARED || {catalog:[],produce:[],seedOils:[],trees:[],i18n:{en:{},so:{}},t:function(_,key){return key;}};
const uiText = (lang,key) => SHARED_AGRI.t(lang,key);
const STANDALONE_WEB = window.location.pathname.indexOf("/web/")===0;
const GIS_ENGINE_URL = STANDALONE_WEB ? "/web/dashboard.html" : "/dashboard";

/* ═════════ MODULE 1 · BACKGROUND SPECTRUM ═════════ */
const SPECTRUM = [
  {id:"red",    label:"Red",    cls:"bg-red-950",    swatch:"#ef4444"},
  {id:"orange", label:"Orange", cls:"bg-orange-950", swatch:"#f97316"},
  {id:"green",  label:"Green",  cls:"bg-emerald-950",swatch:"#10b981"},
  {id:"blue",   label:"Blue",   cls:"bg-blue-950",   swatch:"#3b82f6"},
  {id:"purple", label:"Purple", cls:"bg-violet-950", swatch:"#8b5cf6"},
  {id:"slate",  label:"Slate",  cls:"bg-slate-950",  swatch:"#64748b"},
];

/* ═════════ RECOMMENDATION FORMULA (Module 2) ═════════ */
function phVerdict(ph){
  if (ph < 5.5)  return {status:"Critically Acidic", color:"text-red-300",    chip:"bg-red-900/50 border-red-700 text-red-200",
    rec:"Apply 1,200 kg of Agricultural Lime per acre."};
  if (ph <= 6.2) return {status:"Mildly Acidic",     color:"text-amber-300",  chip:"bg-amber-900/50 border-amber-700 text-amber-200",
    rec:"Apply 500 kg of Maintenance Lime per acre."};
  if (ph > 7.5)  return {status:"Alkaline",          color:"text-sky-300",    chip:"bg-sky-900/50 border-sky-700 text-sky-200",
    rec:"Apply Agricultural Sulfur to lower pH."};
  return {status:"Balanced", color:"text-emerald-300", chip:"bg-emerald-900/50 border-emerald-700 text-emerald-200",
    rec:"No correction required — maintain current fertility program."};
}

/* ═════════ MODULE 5 · FINANCIAL ENGINE (typed amounts) ═════════ */
const TIERS = {
  "Basic pH Test": 25, "Texture + OM Panel": 40,
  "Full Micronutrient Sweep": 85, "Heavy Metal Scan": 120,
};
const PAYMENT_METHODS = ["ZAAD","SAHAL","EDAHAB","CASH","EVCPLUS","BANK"];
const money = x => "$"+Number(x).toFixed(2);
function calcInvoice(base){
  const subtotal=Math.max(0,Number(base)||0);
  return {subtotal:subtotal,total:subtotal};
}
function invStatus(total, paid){
  if (paid <= 0) return "PENDING";
  if (paid < total - 0.005) return "PARTIAL";
  return "PAID";
}

/* ═════════ MODULE 6 · DISEASE INTELLIGENCE VECTOR (Option-2 schema) ═════════ */
const DISEASE_CATEGORIES = ["All","Fruit Trees","Citrus","Grains & Crops","Vegetables","Legumes"];
const DISEASE_CAT_ICONS = {"All":"layers","Fruit Trees":"apple","Citrus":"citrus","Grains & Crops":"wheat","Vegetables":"carrot","Legumes":"sprout"};
/* schema: { cat, plant, disease, cause, symptoms:[…], immediate:[…], remedy } */
const BASE_DISEASE_VECTOR = [
 {cat:"Fruit Trees",plant:"Mango",disease:"Anthracnose",cause:"Colletotrichum gloeosporioides (Fungus)",
  symptoms:["Black tear-streak lesions on ripening fruit","Blossom blight and flower drop","Tar-spot leaf lesions"],
  immediate:["Prune dead panicles and open canopy airflow","Collect and destroy all mummified fruit"],
  remedy:"Copper oxychloride or carbendazim sprays at flowering and fruit set; repeat at 14-day intervals in wet season."},
 {cat:"Fruit Trees",plant:"Banana",disease:"Panama Disease (Fusarium Wilt TR4)",cause:"Fusarium oxysporum f. sp. cubense TR4 (Soil Fungus)",
  symptoms:["Margins of oldest leaves yellow then collapse","Pseudostem base splitting","Brown vascular rings in cut stem"],
  immediate:["Quarantine the infected mat — no suckers or soil may leave","Dig out and burn entire infected stools","Disinfect tools and boots with 10% bleach between farms"],
  remedy:"No chemical cure exists. Replant only with certified resistant GCTCV tissue-culture material; raise soil pH with lime."},
 {cat:"Fruit Trees",plant:"Papaya",disease:"Papaya Ringspot Virus",cause:"Papaya ringspot virus (Virus — aphid vectored)",
  symptoms:["Concentric ringspots on fruit skin","Shoestring / fern-like new leaves","Dark oily petiole streaks"],
  immediate:["Rogue out infected trees within two weeks of symptoms","Control aphid vectors on surrounding weeds"],
  remedy:"No chemical cure. Plant tolerant varieties; reflective silver mulch delays aphid landing and spread."},
 {cat:"Citrus",plant:"Orange & Lime",disease:"Citrus Greening (HLB)",cause:"Candidatus Liberibacter asiaticus (Bacterium — psyllid vectored)",
  symptoms:["Blotchy asymmetrical leaf mottling","Lopsided, bitter, small fruit","Rind stays green on shaded side"],
  immediate:["Remove and burn symptomatic trees completely","Spray for Asian citrus psyllid on new flush"],
  remedy:"No field cure. Use certified HLB-free nursery stock; imidacloprid soil drenches suppress psyllid vectors."},
 {cat:"Citrus",plant:"Lemon",disease:"Citrus Canker",cause:"Xanthomonas citri pv. citri (Bacterium)",
  symptoms:["Raised corky lesions with yellow halos","Lesions on leaves, twigs and fruit","Premature fruit drop"],
  immediate:["Prune only in dry weather; sterilize tools each cut","Install windbreaks to stop wind-driven spread"],
  remedy:"Copper hydroxide sprays on every flush cycle; destroy trees with severe systemic infection."},
 {cat:"Grains & Crops",plant:"Maize",disease:"Fall Armyworm Damage",cause:"Spodoptera frugiperda (Insect pest — larval feeding)",
  symptoms:["Ragged whorl feeding holes","Sawdust-like frass deep inside whorl","Window-paned leaves on young plants"],
  immediate:["Scout at dawn; hand-pick and crush larvae","Pour sand or wood ash into the whorl to abrade larvae"],
  remedy:"Apply emamectin benzoate or Bt biopesticide directly into the whorl at dawn; rotate chemistry to delay resistance."},
 {cat:"Grains & Crops",plant:"Wheat",disease:"Stem Rust",cause:"Puccinia graminis f. sp. tritici (Fungus)",
  symptoms:["Brick-red pustules on stems and sheaths","Ruptured, ragged epidermis around pustules","Lodging in heavily infected stands"],
  immediate:["Rogue early pustuled tillers before sporulation peaks","Avoid late nitrogen that keeps canopy lush"],
  remedy:"Triazole fungicide at flag-leaf stage; deploy Ug99-resistant cultivars across the rotation."},
 {cat:"Grains & Crops",plant:"Sorghum",disease:"Striga (Witchweed) Infestation",cause:"Striga hermonthica (Parasitic flowering plant)",
  symptoms:["Host leaf yellowing despite adequate water","Stunted, wilted sorghum hills","Purple Striga shoots emerging at host base"],
  immediate:["Hand-pull Striga plants before seed set — never let it flower","Rotate out to legume trap crops for 2 seasons"],
  remedy:"Use catch crops (cowpea/groundnut) to induce suicide germination; deploy striga-resistant sorghum varieties."},
 {cat:"Grains & Crops",plant:"Coffee",disease:"Coffee Berry Disease",cause:"Colletotrichum kahawae (Fungus)",
  symptoms:["Dark sunken lesions on green berries","Premature berry fall with lesions intact","Black mummified berries hanging on twigs"],
  immediate:["Strip and burn all infected and mummified berries","Prune canopy for rapid drying after rain"],
  remedy:"Preventative copper or chlorothalonil sprays from flowering, repeating every 4 weeks through berry expansion."},
 {cat:"Vegetables",plant:"Tomato",disease:"Late Blight",cause:"Phytophthora infestans (Oomycete — water mold)",
  symptoms:["Water-soaked grey-green leaf lesions","White mildew on underside in humid morning","Firm brown rot patches on fruit"],
  immediate:["Destroy infected plants immediately — never compost","Hill up soil and stop overhead irrigation"],
  remedy:"Protectant copper or mancozeb; systemics (mefenoxam/metalaxyl) during high-humidity outbreaks."},
 {cat:"Vegetables",plant:"Onion",disease:"Purple Blotch",cause:"Alternaria porri (Fungus)",
  symptoms:["Purple-centered concentric leaf lesions","Yellowing margins, leaf tips collapse","Bulbs soften in storage after infection"],
  immediate:["Remove old infected leaf tissue from the field","Widen spacing; avoid late-evening irrigation"],
  remedy:"Alternate chlorothalonil and mancozeb protectant sprays on a 10-day schedule in humid weather."},
 {cat:"Vegetables",plant:"Cabbage",disease:"Clubroot",cause:"Plasmodiophora brassicae (Soil-borne protist)",
  symptoms:["Swollen, club-shaped deformed roots","Plants stunted with purpling leaves","Midday wilt that recovers overnight"],
  immediate:["Pull and bag infected transplants — do not till them in","Stop machinery movement between infected and clean blocks"],
  remedy:"Lime seedbeds to pH 7.2 before transplanting; 4+ year brassica-free rotation; raised beds for drainage."},
 {cat:"Legumes",plant:"Cowpea",disease:"Aphid-borne Mosaic",cause:"Cowpea aphid-borne mosaic virus (Virus — aphid vectored)",
  symptoms:["Severe leaf mottling and puckering","Distorted, twisted new growth","Stunting and reduced pod set"],
  immediate:["Rogue symptomatic plants at first sign","Yellow sticky traps for aphid monitoring on field edges"],
  remedy:"Certified virus-free seed; reflective mulch repels aphids; resistant IT-series cowpea cultivars."},
 {cat:"Legumes",plant:"Groundnut",disease:"Groundnut Rosette Disease",cause:"Groundnut rosette virus complex (Virus — aphid vectored)",
  symptoms:["Severely shortened internodes (rosette habit)","Uniform bright chlorosis of new leaves","Dwarfed plants with negligible pods"],
  immediate:["Plant dense, synchronous stands early in the season","Rogue stunted rosetted plants weekly"],
  remedy:"Grow aphid-resistant rosette-tolerant cultivars; early dense planting suppresses aphid multiplication."},
 {cat:"Legumes",plant:"Common Bean",disease:"Bean Rust",cause:"Uromyces appendiculatus (Fungus)",
  symptoms:["Cinnamon-brown pustules on leaf undersides","Yellow halos around pustules","Premature defoliation from lower canopy up"],
  immediate:["Strip heavily pustuled lower leaves between rows","Irrigate mornings only — dry foliage by dusk"],
  remedy:"Triadimefon (systemic) at first pustules, or mancozeb protectant weekly through pod fill."},
];
function pathology(cat,plant,disease,cause,symptomA,symptomB,immediate,remedy){
  return {cat,plant,disease,cause,symptoms:[symptomA,symptomB],immediate:[immediate],remedy};
}
const DISEASE_EXPANSION = [
  pathology("Fruit Trees","Mango","Powdery Mildew","Oidium mangiferae (Fungus)","White powder on flowers and young leaves","Poor fruit set and flower drop","Remove heavily infected panicles and improve canopy airflow","Use locally registered sulfur or biological protectants at early bloom according to label guidance."),
  pathology("Fruit Trees","Mango","Bacterial Black Spot","Xanthomonas citri pv. mangiferaeindicae (Bacterium)","Angular black leaf lesions","Raised cracks on fruit skin","Prune infected twigs only during dry weather","Use clean nursery stock, disinfect tools and follow local copper-product guidance."),
  pathology("Fruit Trees","Banana","Black Sigatoka","Pseudocercospora fijiensis (Fungus)","Dark streaks expanding across leaves","Premature collapse of functional leaves","Remove badly spotted leaves without damaging young foliage","Improve spacing and drainage; rotate locally registered fungicide groups when thresholds are exceeded."),
  pathology("Fruit Trees","Banana","Banana Bunchy Top","Banana bunchy top virus (Aphid-vectored virus)","Narrow upright bunched leaves","Dark green dot-dash streaks on veins","Quarantine and destroy confirmed mats with extension guidance","Replant certified virus-free material and manage banana aphid vectors."),
  pathology("Fruit Trees","Papaya","Papaya Anthracnose","Colletotrichum gloeosporioides (Fungus)","Sunken dark fruit lesions","Orange spore masses in humid weather","Remove infected ripe fruit and sanitize harvest crates","Improve field sanitation and apply registered post-flowering protectants when forecast risk is high."),
  pathology("Fruit Trees","Papaya","Papaya Dieback","Phytoplasma or mixed crown infection","Rapid crown yellowing","Stem tip necrosis and plant collapse","Rogue collapsing plants and disinfect cutting tools","Use clean seedlings, control suspected vectors and confirm cause through a diagnostic laboratory."),
  pathology("Fruit Trees","Avocado","Phytophthora Root Rot","Phytophthora cinnamomi (Oomycete)","Sparse pale canopy","Black decayed feeder roots","Prevent irrigation runoff from moving between blocks","Use clean plants, raised drainage, mulch management and registered phosphonate programs where permitted."),
  pathology("Fruit Trees","Avocado","Persea Mite Damage","Oligonychus perseae (Mite)","Brown feeding patches along leaf veins","Webbing and premature leaf drop","Monitor leaf undersides and conserve predatory mites","Use selective miticides only at local economic thresholds and rotate modes of action."),
  pathology("Fruit Trees","Guava","Guava Wilt","Fusarium and Nalanthamala species complex","One-sided branch yellowing","Brown vascular discoloration","Remove dead trees with surrounding infected roots","Improve drainage, avoid root injury and plant tolerant clean nursery material."),
  pathology("Fruit Trees","Guava","Oriental Fruit Fly","Bactrocera dorsalis (Insect)","Oviposition punctures on fruit","Soft fruit containing white larvae","Collect and destroy fallen fruit every week","Use sanitation, protein bait stations and approved male lures within an area-wide program."),
  pathology("Fruit Trees","Pineapple","Phytophthora Heart Rot","Phytophthora nicotianae or P. cinnamomi","Soft water-soaked central leaves","Foul-smelling heart that pulls free","Remove affected plants and drain standing water","Plant treated clean material on raised beds and use locally registered oomycete controls if required."),
  pathology("Fruit Trees","Pineapple","Mealybug Wilt","Pineapple mealybug wilt-associated viruses","Reddish leaf margins curling downward","Root decline with mealybug colonies","Control ants that protect mealybugs","Use clean planting slips and integrated ant and mealybug management."),
  pathology("Fruit Trees","Passion Fruit","Fusarium Wilt","Fusarium oxysporum f. sp. passiflorae","Sudden vine wilting","Brown vascular tissue at collar","Remove infected vines and avoid moving infested soil","Use resistant rootstocks, clean transplants and long non-host rotations."),
  pathology("Fruit Trees","Passion Fruit","Passion Fruit Woodiness","Cowpea aphid-borne mosaic virus complex","Hard deformed fruit","Mosaic and blistered leaves","Rogue symptomatic vines promptly","Use virus-tested seedlings, sanitize tools and manage aphid vectors and weed hosts."),
  pathology("Fruit Trees","Pomegranate","Bacterial Blight","Xanthomonas axonopodis pv. punicae","Oily leaf and fruit spots","Fruit cracking around black lesions","Prune infected twigs and destroy mummified fruit","Use clean cuttings, avoid overhead irrigation and follow registered copper guidance."),
  pathology("Fruit Trees","Date Palm","Bayoud Disease","Fusarium oxysporum f. sp. albedinis","Progressive one-sided frond whitening","Internal reddish-brown vascular streaks","Quarantine suspected palms and restrict offshoot movement","Confirm diagnosis officially and use certified resistant planting material; no curative field treatment is reliable."),
  pathology("Fruit Trees","Coconut","Lethal Yellowing","Phytoplasma transmitted by planthoppers","Premature nut fall","Progressive frond yellowing from lower canopy","Report and remove confirmed palms under local guidance","Plant tolerant cultivars and manage vector habitat as directed by plant-health authorities."),
  pathology("Fruit Trees","Strawberry","Gray Mold","Botrytis cinerea (Fungus)","Gray fuzzy growth on fruit","Flower blight and soft rot","Remove diseased fruit and improve airflow","Keep fruit dry, use clean mulch and rotate registered botrytis products by resistance group."),
  pathology("Citrus","Orange","Citrus Tristeza","Citrus tristeza virus (Aphid-vectored virus)","Tree decline on susceptible rootstock","Stem pitting and small fruit","Remove severe confirmed sources","Use certified budwood, tolerant rootstocks and regional aphid management."),
  pathology("Citrus","Orange","Citrus Black Spot","Phyllosticta citricarpa (Fungus)","Hard black fruit lesions","Premature fruit drop","Remove dead twigs and fallen infected fruit","Improve canopy hygiene and follow local protectant timing from fruit set onward."),
  pathology("Vegetables","Tomato","Bacterial Wilt","Ralstonia solanacearum (Bacterium)","Rapid wilt while leaves remain green","Milky bacterial streaming from cut stem","Remove plants with roots and stop runoff movement","Use clean transplants, resistant varieties, sanitation and multi-year non-host rotation."),
  pathology("Vegetables","Tomato","Fusarium Wilt","Fusarium oxysporum f. sp. lycopersici","Lower-leaf yellowing on one side","Brown vascular rings in stem","Remove infected residue and sanitize equipment","Use resistant cultivars, grafted plants and long rotation with non-host crops."),
  pathology("Vegetables","Tomato","Tomato Leafminer","Tuta absoluta (Insect)","Serpentine leaf mines","Pinholes and galleries in fruit","Remove mined leaves and infested fruit","Use pheromone monitoring, exclusion, biological control and selective registered insecticides only at thresholds."),
  pathology("Vegetables","Potato","Early Blight","Alternaria solani (Fungus)","Concentric target spots on older leaves","Dark sunken tuber lesions","Remove volunteer plants and infected haulms","Maintain balanced fertility and rotate protectant products according to local recommendations."),
  pathology("Vegetables","Potato","Potato Bacterial Wilt","Ralstonia solanacearum species complex","Sudden whole-plant wilt","Brown vascular ring and bacterial ooze","Quarantine seed lots and sanitize tools","Use certified seed, clean irrigation water and extended rotation; report regulated outbreaks."),
  pathology("Vegetables","Onion","Downy Mildew","Peronospora destructor (Oomycete)","Pale elongated leaf patches","Purple-gray sporulation in cool humidity","Improve ventilation and avoid evening irrigation","Rotate allium fields and use locally registered protectants based on weather risk."),
  pathology("Vegetables","Garlic","White Rot","Sclerotium cepivorum (Fungus)","White cottony growth at bulb base","Tiny black sclerotia and leaf collapse","Remove infected bulbs with surrounding soil","Use clean sets and long allium-free rotation; apply approved soil treatments only with specialist guidance."),
  pathology("Vegetables","Cabbage","Black Rot","Xanthomonas campestris pv. campestris","V-shaped yellow lesions from leaf edge","Blackened veins","Remove infected residues and avoid working wet crops","Use hot-water-treated certified seed, rotate brassicas and avoid splash irrigation."),
  pathology("Vegetables","Cabbage","Diamondback Moth","Plutella xylostella (Insect)","Window-pane feeding holes","Small green larvae wriggling on leaves","Scout weekly and conserve parasitoid wasps","Use netting, Bt products and rotate selective registered insecticides by mode of action."),
  pathology("Vegetables","Cauliflower","Downy Mildew","Hyaloperonospora parasitica (Oomycete)","Yellow angular leaf patches","White-gray growth beneath leaves","Remove heavily infected leaves and reduce leaf wetness","Use resistant cultivars, wider spacing and registered protectants when conditions favor disease."),
  pathology("Vegetables","Broccoli","Alternaria Leaf Spot","Alternaria brassicicola or A. brassicae","Dark concentric leaf spots","Black spotting on heads","Remove crop debris and infected seedlings","Use clean seed, brassica rotation and registered protectants if monitoring shows spread."),
  pathology("Vegetables","Carrot","Alternaria Leaf Blight","Alternaria dauci (Fungus)","Brown-edged leaflet lesions","Leaf canopy browning and collapse","Remove infected tops and improve airflow","Use clean seed, rotation and protectant programs based on local disease forecasts."),
  pathology("Vegetables","Carrot","Root-knot Nematode","Meloidogyne species","Forked or galled roots","Patchy stunting","Map affected beds and prevent contaminated soil movement","Rotate with poor hosts, use clean transplants and approved soil-health or biocontrol measures."),
  pathology("Vegetables","Cucumber","Powdery Mildew","Podosphaera xanthii (Fungus)","White powdery leaf colonies","Premature leaf yellowing","Remove badly infected leaves and improve airflow","Use resistant cultivars and rotate registered sulfur, biological or systemic options."),
  pathology("Vegetables","Cucumber","Cucumber Mosaic","Cucumber mosaic virus (Aphid-vectored virus)","Mottled distorted leaves","Stunted vines and malformed fruit","Rogue symptomatic plants and remove weed hosts","Use clean seed, reflective mulch and resistant cultivars; insecticides do not cure infected plants."),
  pathology("Vegetables","Watermelon","Fusarium Wilt","Fusarium oxysporum f. sp. niveum","One-sided vine wilt","Brown vascular discoloration","Remove affected vines and avoid soil transfer","Use resistant varieties, grafting and long rotation outside cucurbit hosts."),
  pathology("Vegetables","Watermelon","Gummy Stem Blight","Stagonosporopsis species (Fungus)","Brown leaf lesions","Gummy cankers on vines","Remove infected vines and cucurbit debris","Use clean seed, rotation, drip irrigation and resistance-managed registered fungicides."),
  pathology("Vegetables","Pumpkin","Powdery Mildew","Podosphaera xanthii (Fungus)","White colonies on mature leaves","Early canopy senescence","Remove severe leaves and reduce dense canopy humidity","Use tolerant varieties and rotate locally registered mildew controls."),
  pathology("Vegetables","Zucchini","Zucchini Yellow Mosaic","Zucchini yellow mosaic virus (Aphid-vectored virus)","Severe yellow mosaic","Narrow leaves and bumpy fruit","Rogue plants promptly and remove volunteer cucurbits","Use resistant seed, reflective mulch and clean field boundaries."),
  pathology("Vegetables","Eggplant","Bacterial Wilt","Ralstonia solanacearum (Bacterium)","Rapid daytime wilt","Bacterial streaming from cut stems","Remove roots and isolate affected irrigation zones","Use resistant rootstocks, sanitation and non-solanaceous rotation."),
  pathology("Vegetables","Chili Pepper","Bacterial Spot","Xanthomonas species complex","Small water-soaked leaf spots","Raised scabby fruit lesions","Remove infected transplants and avoid handling wet plants","Use clean seed, copper-tolerant integrated programs and rotate away from solanaceous hosts."),
  pathology("Vegetables","Chili Pepper","Phytophthora Blight","Phytophthora capsici (Oomycete)","Dark collar lesions","Sudden wilt and fruit rot","Improve drainage and stop contaminated runoff","Use raised beds, resistant varieties and registered oomycete products within an integrated program."),
  pathology("Vegetables","Okra","Yellow Vein Mosaic","Begomovirus complex (Whitefly-vectored virus)","Bright yellow vein network","Small malformed pods","Rogue early infections and remove weed reservoirs","Plant tolerant varieties and manage whitefly vectors with integrated methods."),
  pathology("Vegetables","Lettuce","Downy Mildew","Bremia lactucae (Oomycete)","Angular yellow upper-leaf patches","White growth beneath leaves","Remove infected leaves and lower night humidity","Use resistant cultivars and rotate registered products according to local races."),
  pathology("Vegetables","Spinach","Stemphylium Leaf Spot","Stemphylium botryosum complex","Small gray-brown leaf spots","Lesions merging on marketable leaves","Remove residues and avoid overhead irrigation","Use clean seed, rotation and registered protectants when necessary."),
  pathology("Vegetables","Beetroot","Cercospora Leaf Spot","Cercospora beticola (Fungus)","Circular gray spots with red margins","Premature leaf loss","Remove infected leaves and control volunteer beets","Rotate non-hosts and use resistance-managed registered fungicides when thresholds are reached."),
  pathology("Vegetables","Radish","Clubroot","Plasmodiophora brassicae (Soil-borne protist)","Swollen distorted roots","Stunting and midday wilt","Remove affected roots without spreading soil","Raise pH where agronomically suitable and maintain a long brassica-free rotation."),
  pathology("Vegetables","Sweet Potato","Sweet Potato Weevil","Cylas formicarius (Insect)","Cracked roots with feeding tunnels","Bitter damaged storage roots","Destroy infested residues and promptly hill exposed roots","Use clean vines, pheromone monitoring, timely harvest and field sanitation."),
  pathology("Vegetables","Sweet Potato","Sweet Potato Virus Disease","SPFMV and SPCSV virus complex","Severe leaf mosaic","Stunting and very low root yield","Rogue affected plants and volunteer hosts","Use virus-tested planting vines and manage whitefly and aphid vectors."),
  pathology("Vegetables","Garden Pea","Powdery Mildew","Erysiphe pisi (Fungus)","White powder on leaves and pods","Premature leaf drying","Remove infected residue and avoid late dense planting","Use resistant cultivars and approved sulfur or systemic options when needed."),
  pathology("Grains & Crops","Maize","Maize Streak Virus","Maize streak virus (Leafhopper-vectored virus)","Fine pale streaks along leaves","Severe early stunting","Remove volunteer cereals and very early infected plants","Use resistant varieties, synchronized planting and regional leafhopper management."),
  pathology("Grains & Crops","Maize","Gray Leaf Spot","Cercospora zeae-maydis (Fungus)","Rectangular gray lesions between veins","Premature leaf blight","Bury or decompose infected residue where appropriate","Rotate crops, use tolerant hybrids and apply registered fungicides only when yield risk justifies them."),
  pathology("Grains & Crops","Sorghum","Sorghum Anthracnose","Colletotrichum sublineola (Fungus)","Red-purple leaf lesions","Black fruiting bodies in lesion centers","Remove volunteer sorghum and infected residue","Use resistant cultivars, clean seed and crop rotation."),
  pathology("Grains & Crops","Rice","Rice Blast","Magnaporthe oryzae (Fungus)","Spindle-shaped leaf lesions","Neck rot and empty panicles","Avoid excessive nitrogen and prolonged leaf wetness","Use resistant varieties and registered blast products guided by local forecasts."),
  pathology("Grains & Crops","Wheat","Yellow Rust","Puccinia striiformis f. sp. tritici","Yellow stripe-like pustules","Early leaf drying","Monitor cool-season fields and remove volunteer wheat","Use resistant cultivars and timely registered triazoles when thresholds are exceeded."),
  pathology("Legumes","Common Bean","Angular Leaf Spot","Pseudocercospora griseola (Fungus)","Angular brown lesions limited by veins","Pod spots with dark margins","Remove infected residue and avoid working wet beans","Use clean resistant seed and rotate away from beans for multiple seasons."),
  pathology("Legumes","Common Bean","Common Bacterial Blight","Xanthomonas phaseoli pv. phaseoli","Water-soaked leaf lesions","Greasy pod spots","Use clean seed and sanitize tools","Avoid overhead irrigation and rotate non-hosts; copper may suppress spread where locally registered."),
  pathology("Legumes","Cowpea","Cowpea Bacterial Blight","Xanthomonas axonopodis pv. vignicola","Angular leaf spots with yellow margins","Stem cankers and seed discoloration","Remove infected residues and avoid saving suspect seed","Use certified seed, tolerant varieties and crop rotation."),
  pathology("Legumes","Soybean","Asian Soybean Rust","Phakopsora pachyrhizi (Fungus)","Tiny tan lesions on lower leaves","Dense pustules on leaf undersides","Scout lower canopy during humid weather","Use tolerant varieties and registered fungicides timed to regional alerts."),
  pathology("Legumes","Groundnut","Early Leaf Spot","Passalora arachidicola (Fungus)","Brown spots with yellow halos","Progressive lower-leaf loss","Destroy volunteer groundnuts and rotate fields","Use resistant cultivars and locally recommended protectant schedules."),
  pathology("Grains & Crops","Sesame","Sesame Phyllody","Phytoplasma transmitted by leafhoppers","Flowers transformed into leafy structures","Little or no capsule formation","Rogue affected plants before vectors spread","Use clean seed, control weed hosts and manage leafhopper vectors regionally."),
  pathology("Grains & Crops","Sunflower","Sunflower Downy Mildew","Plasmopara halstedii (Oomycete)","Pale leaves with white underside growth","Systemic stunting and sterile heads","Remove systemic plants and control volunteers","Use resistant hybrids, treated seed where approved and long rotation."),
  pathology("Legumes","Chickpea","Ascochyta Blight","Ascochyta rabiei (Fungus)","Circular leaf and pod lesions","Stem girdling and breakage","Remove infected residue and avoid contaminated seed","Use certified seed, resistant varieties and forecast-guided registered fungicides."),
  pathology("Legumes","Pigeon Pea","Fusarium Wilt","Fusarium udum (Fungus)","Progressive branch wilt","Brown vascular tissue","Remove wilted plants with roots","Use resistant cultivars and long rotation with cereals."),
];
const SHARED_DISEASE_VECTOR = SHARED_AGRI.catalog.flatMap(function(item){
  const cat=item.category==="Fruits"||item.category==="Tree"?"Fruit Trees":item.category==="Vegetables"?"Vegetables":item.family==="Fabaceae"?"Legumes":"Grains & Crops";
  return (item.pathologies||[]).map(function(record){return Object.assign({cat:cat,plant:item.name},record);});
});
const DISEASE_VECTOR = BASE_DISEASE_VECTOR.concat(DISEASE_EXPANSION,SHARED_DISEASE_VECTOR)
  .filter(function(item,index,all){return all.findIndex(function(other){return other.plant===item.plant&&other.disease===item.disease;})===index;});
const FAMILY_PATHOLOGY_TEMPLATES={
 Solanaceae:[
  {disease:"Bacterial Wilt Risk",cause:"Ralstonia solanacearum complex",symptoms:["Rapid green wilt","Vascular browning"],immediate:["Isolate affected beds and sanitize tools"],remedy:"Use clean transplants, resistant material, drainage and non-solanaceous rotation."},
  {disease:"Solanaceous Blight Complex",cause:"Phytophthora and Alternaria species",symptoms:["Expanding leaf lesions","Fruit or stem rot"],immediate:["Remove infected tissue and reduce leaf wetness"],remedy:"Use forecast-led integrated blight management and locally registered products."},
 ],
 Cucurbitaceae:[
  {disease:"Cucurbit Powdery Mildew",cause:"Podosphaera xanthii complex",symptoms:["White powdery colonies","Early canopy decline"],immediate:["Improve airflow and remove badly affected leaves"],remedy:"Use tolerant cultivars and resistance-managed registered mildew controls."},
  {disease:"Cucurbit Mosaic Virus Risk",cause:"Aphid-vectored mosaic virus complex",symptoms:["Mosaic leaves","Bumpy or malformed fruit"],immediate:["Rogue symptomatic plants and remove volunteer hosts"],remedy:"Use clean seed, resistant varieties and integrated vector management."},
 ],
 Fabaceae:[
  {disease:"Legume Rust Complex",cause:"Host-adapted rust fungi",symptoms:["Brown leaf pustules","Premature defoliation"],immediate:["Scout lower leaves and remove severe residues"],remedy:"Use resistant clean seed and registered protection only when thresholds are exceeded."},
  {disease:"Legume Mosaic Virus Risk",cause:"Aphid or whitefly-vectored virus complex",symptoms:["Mosaic and puckering","Stunting and reduced pod set"],immediate:["Rogue symptoms and manage weed hosts"],remedy:"Use certified seed and integrated vector management."},
 ],
 Brassicaceae:[
  {disease:"Clubroot Risk",cause:"Plasmodiophora brassicae",symptoms:["Swollen roots","Midday wilt and stunting"],immediate:["Prevent movement of infested soil"],remedy:"Use resistant cultivars, improve drainage and maintain a long brassica-free rotation."},
  {disease:"Brassica Black Rot",cause:"Xanthomonas campestris pv. campestris",symptoms:["V-shaped yellow lesions","Blackened veins"],immediate:["Remove infected residues and avoid splash irrigation"],remedy:"Use clean treated seed and rotate away from brassicas."},
 ],
 Rutaceae:[
  {disease:"Citrus Greening Risk",cause:"Candidatus Liberibacter · psyllid vectored",symptoms:["Asymmetric mottling","Small lopsided bitter fruit"],immediate:["Inspect new flush and remove confirmed sources"],remedy:"Use certified nursery stock and coordinated psyllid management."},
  {disease:"Citrus Canker Risk",cause:"Xanthomonas citri",symptoms:["Raised corky lesions","Yellow lesion halos"],immediate:["Prune only in dry weather and sanitize tools"],remedy:"Use windbreaks and locally registered copper guidance."},
 ],
 Poaceae:[
  {disease:"Cereal Rust Complex",cause:"Puccinia species",symptoms:["Colored leaf pustules","Premature leaf drying"],immediate:["Scout susceptible growth stages"],remedy:"Use resistant cultivars and threshold-based registered fungicides."},
  {disease:"Cereal Leaf Blight",cause:"Cercospora, Bipolaris or related fungi",symptoms:["Elongated necrotic lesions","Reduced green leaf area"],immediate:["Manage infected residue and volunteers"],remedy:"Rotate crops, balance fertility and use tolerant varieties."},
 ],
 Rosaceae:[
  {disease:"Rosaceae Blossom and Fruit Rot",cause:"Botrytis or Monilinia complex",symptoms:["Blossom blight","Soft fruit rot"],immediate:["Remove mummified fruit and improve airflow"],remedy:"Use sanitation and locally registered bloom protection when weather risk is high."},
 ],
 Arecaceae:[
  {disease:"Palm Bud and Root Rot",cause:"Phytophthora/Thielaviopsis complex",symptoms:["Spear-leaf collapse","Crown or root decay"],immediate:["Improve drainage and isolate affected palms"],remedy:"Confirm diagnosis and use clean planting material with specialist guidance."},
 ],
};
const CATEGORY_PATHOLOGY_TEMPLATES={
 Fruit:[{disease:"Fruit Anthracnose Risk",cause:"Colletotrichum species complex",symptoms:["Sunken fruit lesions","Blossom or twig blight"],immediate:["Remove infected fruit and dead twigs"],remedy:"Improve canopy drying and use locally registered protectants when risk is confirmed."}],
 Vegetable:[{disease:"Root and Crown Rot Risk",cause:"Soil-borne oomycete/fungal complex",symptoms:["Root discoloration","Wilt or crown collapse"],immediate:["Correct drainage and remove confirmed plants"],remedy:"Use clean transplants, rotation and crop-specific registered controls."}],
 Cereal:[{disease:"Seedling and Root Disease Risk",cause:"Pythium, Fusarium or Rhizoctonia complex",symptoms:["Poor emergence","Brown roots and stunting"],immediate:["Check seed quality and soil drainage"],remedy:"Use certified seed, rotation and approved seed protection where required."}],
 Tree:[{disease:"Tree Canker and Dieback Risk",cause:"Opportunistic fungal/bacterial complex",symptoms:["Branch dieback","Sunken bark lesions"],immediate:["Prune dead wood in dry weather and sanitize tools"],remedy:"Reduce stress, protect wounds and confirm the pathogen before treatment."}],
};
function linkedPathologies(cropItem){
 const baseName=(cropItem.baseName||cropItem.name).replace(/ ·.*/,"");
 const key=compact(baseName),direct=DISEASE_VECTOR.filter(record=>{const host=compact(record.plant);return host.includes(key)||key.includes(host);});
 const categoryFallback=cropItem.category==="Tree"?CATEGORY_PATHOLOGY_TEMPLATES.Tree:cropItem.category==="Fruit"?CATEGORY_PATHOLOGY_TEMPLATES.Fruit:CATEGORY_PATHOLOGY_TEMPLATES.Vegetable;
 const templates=(FAMILY_PATHOLOGY_TEMPLATES[cropItem.family]||[]).concat(CATEGORY_PATHOLOGY_TEMPLATES[cropItem.category]||categoryFallback);
 return direct.concat(templates.map(item=>Object.assign({cat:cropItem.category,plant:cropItem.name},item)))
  .filter((item,index,all)=>all.findIndex(other=>other.disease===item.disease)===index).slice(0,6);
}
function loadDiseaseDictionary(){
  return new Promise(function(resolve){setTimeout(function(){resolve(DISEASE_VECTOR.slice());},600);});
}

/* ═════════ MOCK DATA ENGINE ═════════ */
const FARMERS = [
  ["Amina Yusuf","Berbera","sandy loam"],["Mohamed Farah","Afgooye","silt loam"],
  ["Hodan Ali","Hargeysa","clay loam"],["Abdi Warsame","Belet Weyne","alluvial silt"],
  ["Fadumo Hassan","Laascaanood","calcareous loam"],["Idris Osman","Garoowe","gypsic sand"],
  ["Layla Jama","Jowhar","canal silt"],["Hassan Guled","Borama","red loam"],
  ["Nimco Abdi","Kismaayo","alluvial silt"],["Yusuf Elmi","Baydhaba","sandy clay"],
  ["Ayan Sheikh","Dhuusamareeb","aeolian sand"],["Deeqa Muse","Marka","coastal sand"],
];
const PHS = [5.1, 7.9, 5.8, 8.2, 8.1, 7.6, 6.0, 6.8, 8.3, 5.4, 6.5, 7.7];
const today = new Date();

function seedSamples(engineerLine){
  return FARMERS.map(function(f,i){return {
    id:"SMP-"+String(1+i).padStart(3,"0"),
    farmer:f[0], location:f[1], texture:f[2],
    tier:Object.keys(TIERS)[i%4], ph:PHS[i],
    ec:(0.4+(i*0.27)%3.2).toFixed(1), om:(0.5+(i*0.31)%2.4).toFixed(1),
    time:(8+Math.floor(i/2))+":"+((i*17)%60<10?"0":"")+((i*17)%60),
    turnaround:(2.5+(i%5)*0.8), engineer:engineerLine, currency:"USD",
  };});
}
function seedInvoices(samples){
  const methods = PAYMENT_METHODS;
  return samples.slice(0,7).map(function(s,i){
    const base = TIERS[s.tier], gw = methods[(i*3)%methods.length];
    const c = calcInvoice(base);
    const paid = i%3===2 ? Math.round(c.total*0.4*100)/100 : c.total;   // seeded partials
    return {
      id:"INV-2026-"+String(101+i), farmer:s.farmer, tier:s.tier,
      base:base, gw:gw, subtotal:c.subtotal, total:c.total,
      paid:paid, balance:Math.max(0, c.total-paid), currency:"USD",
      status: invStatus(c.total, paid),
      method:(["ZAAD-TXN-8F2A9C","SAHAL-88231-Q","EDAHAB-2219K","CASH-RCP-041","EVC-CP-77220","BNK-TRANS-9912"])[i%6],
      at:(9+i)+":3"+(i%10),
    };
  });
}
function seedMonth(){
  const days = today.getDate();
  return Array.from({length:days},function(_,i){return {
    day:i+1,
    samples:4+Math.round(6*Math.abs(Math.sin(i*0.9))),
    certs:3+Math.round(5*Math.abs(Math.sin(i*0.7+1))),
  };});
}
function seedRevenue(invoices){
  const months=["Mar","Apr","May","Jun","Jul","Aug"];
  const col=invoices.reduce(function(a,v){return a+v.paid;},0);
  const pen=invoices.reduce(function(a,v){return a+v.balance;},0);
  return months.map(function(m,i){return {month:m,
    collected: i===5?col:190+70*i+Math.round(40*Math.abs(Math.sin(i*1.3))),
    pending: i===5?pen:60+35*Math.abs(Math.sin(i))};});
}
const ENGINEERS = [
  {id:1, name:"Eng. Abdisalan Nur",    license:"LIC-2024-0112"},
  {id:2, name:"Eng. Sahra Mohamud",    license:"LIC-2025-0037"},
  {id:3, name:"Eng. Khalid Sheikh",    license:"LIC-2023-0289"},
];

/* ═════════ MODULE 6 · FIVE-YEAR ROTATION DATA ENGINE ═════════ */
const SEASON_SUGGESTIONS = ["Gu","Deyr","Xagaa","Jilaal","Hagaa","Rabi","Kharif","Dry season","Wet season"];
function crop(id,name,category,family,rootDepth,nitrogenDemand,minPh,maxPh,maturityDays,seasons,color){
  return {id,baseId:id,baseName:name,name,category,family,rootDepth,nitrogenDemand,minPh,maxPh,maturityDays,seasons,color};
}
const BASE_CROP_LIBRARY = [
  crop("maize","Maize","Cereal","Poaceae","Medium","Heavy Feeder",5.5,7.5,90,["Gu","Deyr"],"#f59e0b"),
  crop("sorghum","Sorghum","Cereal","Poaceae","Deep","Light Feeder",5.5,8.5,110,["Gu","Xagaa"],"#fb923c"),
  crop("pearl_millet","Pearl Millet","Cereal","Poaceae","Medium","Light Feeder",5.0,8.5,75,["Gu","Xagaa"],"#eab308"),
  crop("rice","Rice","Cereal","Poaceae","Shallow","Heavy Feeder",5.5,7.0,120,["Gu","Deyr"],"#fde047"),
  crop("wheat","Wheat","Cereal","Poaceae","Medium","Heavy Feeder",6.0,7.5,120,["Jilaal","Rabi"],"#d6b981"),
  crop("barley","Barley","Cereal","Poaceae","Medium","Light Feeder",6.0,8.0,100,["Jilaal","Rabi"],"#c4a46b"),
  crop("cowpea","Cowpea","Legume","Fabaceae","Deep","Nitrogen Fixer",5.5,7.5,75,["Gu","Deyr"],"#22c55e"),
  crop("beans","Common Beans","Legume","Fabaceae","Medium","Nitrogen Fixer",5.5,7.5,85,["Gu","Deyr"],"#10b981"),
  crop("mung_bean","Mung Bean","Legume","Fabaceae","Medium","Nitrogen Fixer",6.0,7.5,65,["Gu","Deyr"],"#34d399"),
  crop("groundnut","Groundnut","Legume","Fabaceae","Medium","Nitrogen Fixer",5.8,7.2,110,["Gu"],"#84cc16"),
  crop("soybean","Soybean","Legume","Fabaceae","Deep","Nitrogen Fixer",6.0,7.0,120,["Gu"],"#65a30d"),
  crop("chickpea","Chickpea","Legume","Fabaceae","Deep","Nitrogen Fixer",6.0,8.0,110,["Jilaal","Rabi"],"#a3e635"),
  crop("pigeon_pea","Pigeon Pea","Legume","Fabaceae","Deep","Nitrogen Fixer",5.0,8.0,180,["Gu"],"#4d7c0f"),
  crop("green_manure","Green Manure","Cover Crop","Fabaceae","Medium","Nitrogen Fixer",5.5,7.8,60,["Any window"],"#059669"),
  crop("sesame","Sesame","Oilseed","Pedaliaceae","Deep","Light Feeder",5.5,8.0,100,["Gu","Deyr"],"#facc15"),
  crop("sunflower","Sunflower","Oilseed","Asteraceae","Deep","Heavy Feeder",6.0,7.5,110,["Gu"],"#fbbf24"),

  crop("tomato","Tomato","Vegetable","Solanaceae","Deep","Heavy Feeder",5.5,7.5,100,["Deyr","Irrigated Jilaal"],"#ef4444"),
  crop("onion","Onion","Vegetable","Amaryllidaceae","Shallow","Heavy Feeder",6.0,7.2,120,["Deyr","Jilaal"],"#a78bfa"),
  crop("garlic","Garlic","Vegetable","Amaryllidaceae","Shallow","Heavy Feeder",6.0,7.5,150,["Jilaal"],"#c4b5fd"),
  crop("watermelon","Watermelon","Vegetable","Cucurbitaceae","Deep","Heavy Feeder",5.5,7.5,90,["Gu","Xagaa"],"#f43f5e"),
  crop("butternut","Butternut Squash","Vegetable","Cucurbitaceae","Deep","Heavy Feeder",5.8,7.2,110,["Gu","Deyr"],"#f97316"),
  crop("red_kuri","Red Kuri Squash","Vegetable","Cucurbitaceae","Deep","Heavy Feeder",5.8,7.2,100,["Gu","Deyr"],"#dc2626"),
  crop("pumpkin","Pumpkin","Vegetable","Cucurbitaceae","Deep","Heavy Feeder",5.8,7.5,110,["Gu"],"#ea580c"),
  crop("zucchini","Zucchini","Vegetable","Cucurbitaceae","Medium","Heavy Feeder",6.0,7.5,55,["Gu","Deyr"],"#4ade80"),
  crop("cucumber","Cucumber","Vegetable","Cucurbitaceae","Shallow","Heavy Feeder",5.8,7.0,65,["Gu","Deyr"],"#2dd4bf"),
  crop("cabbage","Cabbage","Vegetable","Brassicaceae","Shallow","Heavy Feeder",6.0,7.5,100,["Deyr","Jilaal"],"#14b8a6"),
  crop("cauliflower","Cauliflower","Vegetable","Brassicaceae","Shallow","Heavy Feeder",6.0,7.5,100,["Deyr","Jilaal"],"#e2e8f0"),
  crop("broccoli","Broccoli","Vegetable","Brassicaceae","Shallow","Heavy Feeder",6.0,7.5,90,["Deyr","Jilaal"],"#16a34a"),
  crop("carrot","Carrot","Vegetable","Apiaceae","Medium","Light Feeder",6.0,7.0,90,["Deyr","Jilaal"],"#fb923c"),
  crop("potato","Potato","Vegetable","Solanaceae","Shallow","Heavy Feeder",5.0,6.5,100,["Deyr","Jilaal"],"#ca8a04"),
  crop("sweet_potato","Sweet Potato","Vegetable","Convolvulaceae","Deep","Heavy Feeder",5.5,6.8,120,["Gu","Deyr"],"#c2410c"),
  crop("okra","Okra","Vegetable","Malvaceae","Deep","Light Feeder",6.0,7.5,70,["Gu","Xagaa"],"#22c55e"),
  crop("eggplant","Eggplant","Vegetable","Solanaceae","Deep","Heavy Feeder",5.5,7.2,120,["Gu","Deyr"],"#7c3aed"),
  crop("chili_pepper","Chili Pepper","Vegetable","Solanaceae","Medium","Heavy Feeder",5.8,7.0,120,["Gu","Deyr"],"#dc2626"),
  crop("lettuce","Lettuce","Vegetable","Asteraceae","Shallow","Heavy Feeder",6.0,7.0,50,["Deyr","Jilaal"],"#86efac"),
  crop("spinach","Spinach","Vegetable","Amaranthaceae","Shallow","Heavy Feeder",6.0,7.5,45,["Deyr","Jilaal"],"#15803d"),
  crop("beetroot","Beetroot","Vegetable","Amaranthaceae","Medium","Heavy Feeder",6.0,7.5,70,["Deyr","Jilaal"],"#be123c"),

  crop("banana","Banana","Fruit","Musaceae","Shallow","Heavy Feeder",5.5,7.5,365,["Year-round irrigation"],"#fde047"),
  crop("mango","Mango","Fruit","Anacardiaceae","Deep","Light Feeder",5.5,8.0,1095,["Gu establishment"],"#fbbf24"),
  crop("papaya","Papaya","Fruit","Caricaceae","Medium","Heavy Feeder",5.5,7.0,270,["Gu","Year-round irrigation"],"#f97316"),
  crop("orange","Sweet Orange","Fruit","Rutaceae","Deep","Heavy Feeder",5.5,7.5,730,["Gu establishment"],"#fb923c"),
  crop("lime","Lime","Fruit","Rutaceae","Deep","Heavy Feeder",5.5,7.5,600,["Gu establishment"],"#84cc16"),
  crop("guava","Guava","Fruit","Myrtaceae","Deep","Light Feeder",5.0,7.5,730,["Gu","Deyr establishment"],"#4ade80"),
  crop("avocado","Avocado","Fruit","Lauraceae","Deep","Heavy Feeder",5.5,7.0,1095,["Gu establishment"],"#65a30d"),
  crop("date_palm","Date Palm","Fruit","Arecaceae","Deep","Heavy Feeder",7.0,8.5,1825,["Irrigated establishment"],"#a16207"),
  crop("pomegranate","Pomegranate","Fruit","Lythraceae","Deep","Light Feeder",5.5,7.5,730,["Gu establishment"],"#e11d48"),
  crop("passion_fruit","Passion Fruit","Fruit","Passifloraceae","Medium","Heavy Feeder",5.5,6.8,300,["Gu","Deyr"],"#9333ea"),
  crop("pineapple","Pineapple","Fruit","Bromeliaceae","Shallow","Heavy Feeder",4.5,6.5,540,["Gu establishment"],"#eab308"),
  crop("strawberry","Strawberry","Fruit","Rosaceae","Shallow","Heavy Feeder",5.5,6.8,120,["Deyr","Jilaal"],"#f43f5e"),
  crop("melon","Melon","Fruit","Cucurbitaceae","Medium","Heavy Feeder",5.8,7.2,80,["Gu","Xagaa"],"#fcd34d"),
  crop("coconut","Coconut","Fruit","Arecaceae","Deep","Heavy Feeder",5.5,8.0,1825,["Gu establishment"],"#92400e"),
];
function cropVariety(id,name,baseId,maturityDays,seasons){
  const base=BASE_CROP_LIBRARY.find(function(item){return item.id===baseId;});
  return Object.assign({},base,{id,baseId:baseId,baseName:base.name,name,maturityDays:maturityDays||base.maturityDays,seasons:seasons||base.seasons});
}
const CROP_VARIETY_EXPANSION = [
  cropVariety("tomato_roma_vf","Tomato · Roma VF","tomato",85),
  cropVariety("tomato_money_maker","Tomato · Money Maker","tomato",90),
  cropVariety("tomato_cherry_sweet_100","Tomato · Cherry Sweet 100","tomato",70),
  cropVariety("tomato_rio_grande","Tomato · Rio Grande","tomato",95),
  cropVariety("tomato_marglobe","Tomato · Marglobe","tomato",80),
  cropVariety("onion_red_creole","Onion · Red Creole","onion",115),
  cropVariety("onion_texas_grano","Onion · Texas Grano","onion",110),
  cropVariety("onion_bombay_red","Onion · Bombay Red","onion",120),
  cropVariety("onion_white_lisbon","Onion · White Lisbon","onion",65),
  cropVariety("pepper_california_wonder","Pepper · California Wonder","chili_pepper",75),
  cropVariety("pepper_cayenne_long_slim","Pepper · Cayenne Long Slim","chili_pepper",80),
  cropVariety("pepper_scotch_bonnet","Pepper · Scotch Bonnet","chili_pepper",100),
  cropVariety("pepper_birds_eye","Pepper · Bird's Eye","chili_pepper",95),
  cropVariety("cabbage_copenhagen_market","Cabbage · Copenhagen Market","cabbage",72),
  cropVariety("cabbage_gloria_f1","Cabbage · Gloria F1","cabbage",80),
  cropVariety("cabbage_drumhead","Cabbage · Drumhead","cabbage",105),
  cropVariety("cabbage_red_acre","Cabbage · Red Acre","cabbage",76),
  cropVariety("carrot_nantes","Carrot · Nantes","carrot",75),
  cropVariety("carrot_chantenay","Carrot · Chantenay","carrot",70),
  cropVariety("carrot_kuroda","Carrot · Kuroda","carrot",90),
  cropVariety("potato_desiree","Potato · Desiree","potato",110),
  cropVariety("potato_shangi","Potato · Shangi","potato",90),
  cropVariety("potato_kenya_mpya","Potato · Kenya Mpya","potato",100),
  cropVariety("sweet_potato_beauregard","Sweet Potato · Beauregard","sweet_potato",105),
  cropVariety("sweet_potato_kabode","Sweet Potato · Kabode","sweet_potato",120),
  cropVariety("sweet_potato_vita","Sweet Potato · Vita","sweet_potato",115),
  cropVariety("cucumber_marketmore_76","Cucumber · Marketmore 76","cucumber",65),
  cropVariety("cucumber_poinsett_76","Cucumber · Poinsett 76","cucumber",60),
  cropVariety("cucumber_ashley","Cucumber · Ashley","cucumber",65),
  cropVariety("watermelon_crimson_sweet","Watermelon · Crimson Sweet","watermelon",85),
  cropVariety("watermelon_sugar_baby","Watermelon · Sugar Baby","watermelon",75),
  cropVariety("watermelon_charleston_gray","Watermelon · Charleston Gray","watermelon",95),
  cropVariety("pumpkin_musquee_provence","Pumpkin · Musquée de Provence","pumpkin",120),
  cropVariety("pumpkin_connecticut_field","Pumpkin · Connecticut Field","pumpkin",110),
  cropVariety("eggplant_black_beauty","Eggplant · Black Beauty","eggplant",85),
  cropVariety("eggplant_long_purple","Eggplant · Long Purple","eggplant",80),
  cropVariety("okra_clemson_spineless","Okra · Clemson Spineless","okra",60),
  cropVariety("okra_emerald_green","Okra · Emerald Green","okra",58),
  cropVariety("lettuce_great_lakes","Lettuce · Great Lakes","lettuce",75),
  cropVariety("lettuce_buttercrunch","Lettuce · Buttercrunch","lettuce",55),
  cropVariety("spinach_fordhook_giant","Spinach · Fordhook Giant","spinach",50),
  cropVariety("spinach_bloomsdale","Spinach · Bloomsdale","spinach",45),
  cropVariety("cauliflower_snowball","Cauliflower · Snowball","cauliflower",85),
  cropVariety("cauliflower_amazing","Cauliflower · Amazing","cauliflower",75),
  cropVariety("broccoli_calabrese","Broccoli · Calabrese","broccoli",85),
  cropVariety("broccoli_green_magic","Broccoli · Green Magic","broccoli",65),
  cropVariety("beetroot_detroit_dark_red","Beetroot · Detroit Dark Red","beetroot",60),
  cropVariety("beetroot_cylindra","Beetroot · Cylindra","beetroot",65),
  crop("radish_cherry_belle","Radish · Cherry Belle","Vegetable","Brassicaceae","Shallow","Light Feeder",5.8,7.0,25,["Deyr","Jilaal"],"#ef4444"),
  crop("radish_french_breakfast","Radish · French Breakfast","Vegetable","Brassicaceae","Shallow","Light Feeder",5.8,7.0,28,["Deyr","Jilaal"],"#fb7185"),
  crop("garden_pea_lincoln","Garden Pea · Lincoln","Vegetable","Fabaceae","Medium","Nitrogen Fixer",6.0,7.5,70,["Jilaal","Rabi"],"#22c55e"),
  crop("sugar_snap_pea","Garden Pea · Sugar Snap","Vegetable","Fabaceae","Medium","Nitrogen Fixer",6.0,7.5,65,["Jilaal","Rabi"],"#4ade80"),
  cropVariety("mango_apple","Mango · Apple","mango",900),
  cropVariety("mango_kent","Mango · Kent","mango",1000),
  cropVariety("mango_keitt","Mango · Keitt","mango",1050),
  cropVariety("mango_tommy_atkins","Mango · Tommy Atkins","mango",950),
  cropVariety("banana_grand_nain","Banana · Grand Nain","banana",330),
  cropVariety("banana_williams","Banana · Williams","banana",350),
  cropVariety("banana_dwarf_cavendish","Banana · Dwarf Cavendish","banana",320),
  cropVariety("papaya_solo_sunrise","Papaya · Solo Sunrise","papaya",260),
  cropVariety("papaya_red_lady","Papaya · Red Lady","papaya",250),
  cropVariety("orange_valencia","Orange · Valencia","orange",700),
  cropVariety("orange_washington_navel","Orange · Washington Navel","orange",730),
  cropVariety("avocado_hass","Avocado · Hass","avocado",1000),
  cropVariety("avocado_fuerte","Avocado · Fuerte","avocado",950),
  cropVariety("guava_allahabad_safeda","Guava · Allahabad Safeda","guava",650),
  cropVariety("guava_ruby_supreme","Guava · Ruby Supreme","guava",680),
  cropVariety("pineapple_smooth_cayenne","Pineapple · Smooth Cayenne","pineapple",520),
  cropVariety("pineapple_md2","Pineapple · MD2","pineapple",500),
  cropVariety("passion_purple_possum","Passion Fruit · Purple Possum","passion_fruit",290),
  cropVariety("passion_yellow_giant","Passion Fruit · Yellow Giant","passion_fruit",310),
  cropVariety("pomegranate_wonderful","Pomegranate · Wonderful","pomegranate",700),
  cropVariety("date_medjool","Date Palm · Medjool","date_palm",1800),
  cropVariety("date_barhi","Date Palm · Barhi","date_palm",1750),
  cropVariety("strawberry_chandler","Strawberry · Chandler","strawberry",115),
  cropVariety("strawberry_festival","Strawberry · Festival","strawberry",110),
];
const REGIONAL_PRODUCE_EXPANSION = [
  crop("african_nightshade","African Nightshade (Managu)","Vegetable","Solanaceae","Medium","Light Feeder",5.5,7.2,45,["Gu","Deyr"],"#166534"),
  crop("amaranth_mchicha","Leaf Amaranth (Mchicha)","Vegetable","Amaranthaceae","Shallow","Light Feeder",5.5,7.5,35,["Gu","Deyr"],"#22c55e"),
  crop("spider_plant_saga","Spider Plant (Saga)","Vegetable","Cleomaceae","Medium","Light Feeder",5.5,7.5,45,["Gu","Deyr"],"#65a30d"),
  crop("jute_mallow_molokhia","Jute Mallow (Molokhia)","Vegetable","Malvaceae","Medium","Light Feeder",5.5,7.5,55,["Gu","Xagaa"],"#15803d"),
  crop("ethiopian_kale","Ethiopian Kale (Gomen)","Vegetable","Brassicaceae","Medium","Heavy Feeder",6.0,7.5,70,["Deyr","Jilaal"],"#16a34a"),
  crop("sukuma_wiki","Collard Greens (Sukuma Wiki)","Vegetable","Brassicaceae","Medium","Heavy Feeder",6.0,7.5,65,["Gu","Deyr"],"#4d7c0f"),
  crop("african_eggplant","African Eggplant","Vegetable","Solanaceae","Deep","Heavy Feeder",5.5,7.2,100,["Gu","Deyr"],"#7e22ce"),
  crop("garden_egg_white","Garden Egg · White","Vegetable","Solanaceae","Deep","Heavy Feeder",5.5,7.2,90,["Gu","Deyr"],"#e2e8f0"),
  crop("garden_egg_green","Garden Egg · Green","Vegetable","Solanaceae","Deep","Heavy Feeder",5.5,7.2,90,["Gu","Deyr"],"#84cc16"),
  crop("bottle_gourd","Bottle Gourd","Vegetable","Cucurbitaceae","Deep","Heavy Feeder",5.8,7.5,90,["Gu","Xagaa"],"#65a30d"),
  crop("ridge_gourd","Ridge Gourd","Vegetable","Cucurbitaceae","Medium","Heavy Feeder",5.8,7.5,70,["Gu","Deyr"],"#22c55e"),
  crop("sponge_gourd","Sponge Gourd (Luffa)","Vegetable","Cucurbitaceae","Medium","Heavy Feeder",5.8,7.5,80,["Gu","Deyr"],"#4ade80"),
  crop("bitter_melon","Bitter Melon","Vegetable","Cucurbitaceae","Medium","Heavy Feeder",5.5,7.0,70,["Gu","Deyr"],"#16a34a"),
  crop("chayote","Chayote","Vegetable","Cucurbitaceae","Deep","Heavy Feeder",5.5,7.5,150,["Gu establishment"],"#86efac"),
  crop("cassava","Cassava","Vegetable","Euphorbiaceae","Deep","Heavy Feeder",5.0,7.0,300,["Gu"],"#a16207"),
  crop("taro","Taro","Vegetable","Araceae","Shallow","Heavy Feeder",5.5,7.0,240,["Gu","Irrigated"],"#15803d"),
  crop("cocoyam","Cocoyam","Vegetable","Araceae","Shallow","Heavy Feeder",5.5,7.0,270,["Gu","Irrigated"],"#166534"),
  crop("white_guinea_yam","White Guinea Yam","Vegetable","Dioscoreaceae","Deep","Heavy Feeder",5.5,7.0,270,["Gu"],"#92400e"),
  crop("yellow_guinea_yam","Yellow Guinea Yam","Vegetable","Dioscoreaceae","Deep","Heavy Feeder",5.5,7.0,300,["Gu"],"#a16207"),
  crop("arrowroot","Arrowroot","Vegetable","Marantaceae","Shallow","Heavy Feeder",5.5,7.0,300,["Gu","Irrigated"],"#ca8a04"),
  crop("moringa_leaf","Moringa Leaves","Vegetable","Moringaceae","Deep","Light Feeder",6.0,8.5,120,["Gu establishment"],"#22c55e"),
  crop("cowpea_leaf","Cowpea Leaves","Vegetable","Fabaceae","Medium","Nitrogen Fixer",5.5,7.5,35,["Gu","Deyr"],"#4ade80"),
  crop("pumpkin_leaf","Pumpkin Leaves","Vegetable","Cucurbitaceae","Deep","Heavy Feeder",5.8,7.5,40,["Gu","Deyr"],"#84cc16"),
  crop("roselle_leaf","Roselle Leaves","Vegetable","Malvaceae","Deep","Light Feeder",5.5,7.5,75,["Gu"],"#be123c"),
  crop("fenugreek","Fenugreek","Vegetable","Fabaceae","Medium","Nitrogen Fixer",6.0,7.5,90,["Jilaal","Rabi"],"#65a30d"),
  crop("fava_bean","Fava Bean","Vegetable","Fabaceae","Medium","Nitrogen Fixer",6.0,8.0,110,["Jilaal","Rabi"],"#22c55e"),
  crop("leek","Leek","Vegetable","Amaryllidaceae","Shallow","Heavy Feeder",6.0,7.5,120,["Deyr","Jilaal"],"#34d399"),
  crop("turnip","Turnip","Vegetable","Brassicaceae","Medium","Light Feeder",5.8,7.5,60,["Deyr","Jilaal"],"#e2e8f0"),
  crop("globe_artichoke","Globe Artichoke","Vegetable","Asteraceae","Deep","Heavy Feeder",6.0,7.5,180,["Jilaal"],"#6d28d9"),
  crop("rocket_arugula","Rocket (Arugula)","Vegetable","Brassicaceae","Shallow","Light Feeder",6.0,7.5,40,["Deyr","Jilaal"],"#4ade80"),
  crop("parsley","Parsley","Vegetable","Apiaceae","Medium","Light Feeder",5.8,7.2,75,["Deyr","Jilaal"],"#15803d"),
  crop("coriander","Coriander (Cilantro)","Vegetable","Apiaceae","Shallow","Light Feeder",6.0,7.5,45,["Deyr","Jilaal"],"#22c55e"),
  crop("mint","Mint","Vegetable","Lamiaceae","Shallow","Heavy Feeder",6.0,7.5,60,["Irrigated year-round"],"#2dd4bf"),
  crop("swiss_chard","Swiss Chard","Vegetable","Amaranthaceae","Medium","Heavy Feeder",6.0,7.5,60,["Deyr","Jilaal"],"#e11d48"),
  crop("celery","Celery","Vegetable","Apiaceae","Shallow","Heavy Feeder",6.0,7.0,120,["Jilaal","Irrigated"],"#4ade80"),
  crop("asparagus","Asparagus","Vegetable","Asparagaceae","Deep","Heavy Feeder",6.5,7.5,730,["Jilaal establishment"],"#16a34a"),
  crop("kiwano","African Horned Melon (Kiwano)","Fruit","Cucurbitaceae","Medium","Heavy Feeder",6.0,7.5,110,["Gu","Xagaa"],"#f97316"),
  crop("tamarind","Tamarind","Fruit","Fabaceae","Deep","Light Feeder",5.5,7.5,1460,["Gu establishment"],"#92400e"),
  crop("baobab_fruit","Baobab Fruit","Fruit","Malvaceae","Deep","Light Feeder",5.5,8.0,1825,["Gu establishment"],"#a16207"),
  crop("jujube","Jujube (Ber)","Fruit","Rhamnaceae","Deep","Light Feeder",6.0,8.5,730,["Gu establishment"],"#b45309"),
  crop("marula","Marula","Fruit","Anacardiaceae","Deep","Light Feeder",5.5,7.5,1460,["Gu establishment"],"#d97706"),
  crop("safou","African Pear (Safou)","Fruit","Burseraceae","Deep","Heavy Feeder",5.0,7.0,1095,["Gu establishment"],"#4338ca"),
  crop("jackfruit","Jackfruit","Fruit","Moraceae","Deep","Heavy Feeder",5.5,7.5,1095,["Gu establishment"],"#84cc16"),
  crop("breadfruit","Breadfruit","Fruit","Moraceae","Deep","Heavy Feeder",6.0,7.5,1095,["Gu establishment"],"#65a30d"),
  crop("soursop","Soursop","Fruit","Annonaceae","Deep","Heavy Feeder",5.5,6.5,730,["Gu establishment"],"#4ade80"),
  crop("custard_apple","Custard Apple","Fruit","Annonaceae","Deep","Light Feeder",6.0,7.5,730,["Gu establishment"],"#a3e635"),
  crop("cherimoya","Cherimoya","Fruit","Annonaceae","Deep","Heavy Feeder",6.0,7.0,900,["Cool-season establishment"],"#84cc16"),
  crop("fig","Common Fig","Fruit","Moraceae","Deep","Light Feeder",6.0,8.0,730,["Jilaal establishment"],"#7c3aed"),
  crop("olive","Olive","Fruit","Oleaceae","Deep","Light Feeder",6.5,8.5,1460,["Jilaal establishment"],"#4d7c0f"),
  crop("grape_thompson","Grape · Thompson Seedless","Fruit","Vitaceae","Deep","Heavy Feeder",5.5,7.0,730,["Jilaal establishment"],"#84cc16"),
  crop("grape_flame","Grape · Flame Seedless","Fruit","Vitaceae","Deep","Heavy Feeder",5.5,7.0,730,["Jilaal establishment"],"#e11d48"),
  crop("apricot","Apricot","Fruit","Rosaceae","Deep","Heavy Feeder",6.0,7.5,1095,["Cool Jilaal establishment"],"#fb923c"),
  crop("peach","Peach","Fruit","Rosaceae","Deep","Heavy Feeder",6.0,7.0,900,["Cool Jilaal establishment"],"#f97316"),
  crop("plum","Plum","Fruit","Rosaceae","Deep","Heavy Feeder",6.0,7.0,1095,["Cool Jilaal establishment"],"#7e22ce"),
  crop("pear","Pear","Fruit","Rosaceae","Deep","Heavy Feeder",6.0,7.0,1095,["Cool Jilaal establishment"],"#a3e635"),
  crop("apple_anna","Apple · Anna","Fruit","Rosaceae","Deep","Heavy Feeder",6.0,7.0,1095,["Highland establishment"],"#ef4444"),
  crop("quince","Quince","Fruit","Rosaceae","Deep","Heavy Feeder",6.0,7.5,1095,["Highland establishment"],"#eab308"),
  crop("loquat","Loquat","Fruit","Rosaceae","Deep","Heavy Feeder",6.0,7.5,900,["Gu establishment"],"#f59e0b"),
  crop("mulberry","Mulberry","Fruit","Moraceae","Deep","Light Feeder",5.5,7.5,730,["Gu establishment"],"#581c87"),
  crop("lychee","Lychee","Fruit","Sapindaceae","Deep","Heavy Feeder",5.0,6.5,1460,["Humid Gu establishment"],"#e11d48"),
  crop("longan","Longan","Fruit","Sapindaceae","Deep","Heavy Feeder",5.5,6.5,1460,["Humid Gu establishment"],"#a16207"),
  crop("rambutan","Rambutan","Fruit","Sapindaceae","Deep","Heavy Feeder",5.0,6.5,1460,["Humid Gu establishment"],"#dc2626"),
  crop("dragon_fruit","Dragon Fruit","Fruit","Cactaceae","Shallow","Light Feeder",5.5,7.0,365,["Dry irrigated establishment"],"#ec4899"),
  crop("grapefruit","Grapefruit","Fruit","Rutaceae","Deep","Heavy Feeder",5.5,7.5,900,["Gu establishment"],"#f59e0b"),
  crop("mandarin","Mandarin","Fruit","Rutaceae","Deep","Heavy Feeder",5.5,7.5,730,["Gu establishment"],"#f97316"),
  crop("clementine","Clementine","Fruit","Rutaceae","Deep","Heavy Feeder",5.5,7.5,730,["Gu establishment"],"#fb923c"),
  crop("pomelo","Pomelo","Fruit","Rutaceae","Deep","Heavy Feeder",5.5,7.5,900,["Gu establishment"],"#84cc16"),
  crop("lemon_eureka","Lemon · Eureka","Fruit","Rutaceae","Deep","Heavy Feeder",5.5,7.5,650,["Gu establishment"],"#fde047"),
  crop("date_ajwa","Date Palm · Ajwa","Fruit","Arecaceae","Deep","Heavy Feeder",7.0,8.5,1825,["Irrigated establishment"],"#78350f"),
  crop("date_deglet_noor","Date Palm · Deglet Noor","Fruit","Arecaceae","Deep","Heavy Feeder",7.0,8.5,1825,["Irrigated establishment"],"#92400e"),
  crop("mango_ngowe","Mango · Ngowe","Fruit","Anacardiaceae","Deep","Light Feeder",5.5,8.0,950,["Gu establishment"],"#f59e0b"),
  crop("mango_boribo","Mango · Boribo","Fruit","Anacardiaceae","Deep","Light Feeder",5.5,8.0,950,["Gu establishment"],"#eab308"),
  crop("matoke","East African Highland Banana (Matoke)","Fruit","Musaceae","Shallow","Heavy Feeder",5.5,7.5,365,["Year-round irrigation"],"#84cc16"),
  crop("kisii_banana","Kisii Banana","Fruit","Musaceae","Shallow","Heavy Feeder",5.5,7.5,360,["Year-round irrigation"],"#fde047"),
  crop("prickly_pear","Prickly Pear","Fruit","Cactaceae","Shallow","Light Feeder",6.0,8.5,365,["Dry-season establishment"],"#f43f5e"),
  crop("moringa_tree","Moringa Tree","Tree","Moringaceae","Deep","Light Feeder",6.0,8.5,365,["Gu establishment"],"#16a34a"),
  crop("neem_tree","Neem Tree","Tree","Meliaceae","Deep","Light Feeder",6.0,8.5,1095,["Gu establishment"],"#166534"),
  crop("gum_arabic_acacia","Gum Arabic Acacia","Tree","Fabaceae","Deep","Nitrogen Fixer",6.0,8.0,1460,["Gu establishment"],"#65a30d"),
  crop("frankincense_tree","Frankincense Tree","Tree","Burseraceae","Deep","Light Feeder",7.0,8.5,1825,["Dry upland establishment"],"#a8a29e"),
  crop("myrrh_tree","Myrrh Tree","Tree","Burseraceae","Deep","Light Feeder",6.5,8.0,1460,["Dry upland establishment"],"#78716c"),
];
function sharedCropRecord(item){
  const category=item.category==="Fruits"?"Fruit":item.category==="Vegetables"?"Vegetable":item.category;
  const record=Object.assign({},item,{category:category,baseId:item.baseId||item.id,baseName:item.name,color:item.color||"#64748b"});
  record.pathologies=(record.pathologies||[]).concat(linkedPathologies(record)).filter(function(entry,index,all){return all.findIndex(function(other){return other.disease===entry.disease;})===index;}).slice(0,8);
  return record;
}
const SHARED_CROP_LIBRARY = SHARED_AGRI.catalog.map(sharedCropRecord);
const LIMS_STATIC_SEED_OILS=[
 crop("oil_sesame","Sesame","Seed Oil","Pedaliaceae","Deep","Light Feeder",5.5,8,100,["Gu","Deyr"],"#d97706"),
 crop("oil_palm","Oil Palm","Seed Oil","Arecaceae","Deep","Heavy Feeder",4,7,1095,["Humid establishment"],"#d97706"),
 crop("oil_sunflower","Sunflower","Seed Oil","Asteraceae","Deep","Heavy Feeder",6,7.5,110,["Gu"],"#d97706"),
 crop("oil_castor","Castor","Seed Oil","Euphorbiaceae","Deep","Light Feeder",5.5,7.5,150,["Gu"],"#d97706"),
 crop("oil_niger","Niger Seed","Seed Oil","Asteraceae","Medium","Light Feeder",5.2,7.5,120,["Gu"],"#d97706"),
 crop("oil_olive","Olive","Seed Oil","Oleaceae","Deep","Light Feeder",6.5,8.5,1460,["Jilaal establishment"],"#d97706"),
 crop("oil_jojoba","Jojoba","Seed Oil","Simmondsiaceae","Deep","Light Feeder",6,8.5,1095,["Dry irrigated establishment"],"#d97706"),
].map(item=>Object.assign({},item,{categorySo:"Saliidda Abuurka",pathologies:linkedPathologies(item)}));
const CROP_LIBRARY = BASE_CROP_LIBRARY.concat(CROP_VARIETY_EXPANSION,REGIONAL_PRODUCE_EXPANSION,LIMS_STATIC_SEED_OILS,SHARED_CROP_LIBRARY)
  .filter(function(item,index,all){return all.findIndex(function(other){return other.id===item.id;})===index;})
  .map(function(item){
    const linked=(item.pathologies||[]).concat(linkedPathologies(item)).filter(function(record,index,all){return all.findIndex(function(other){return other.disease===record.disease;})===index;});
    return Object.assign({},item,{pathologies:linked.slice(0,8)});
  });
const CROP_ALIASES = {
  corn:"maize",cornmeal:"maize",millet:"pearl_millet",pearlmillet:"pearl_millet",
  bean:"beans",commonbean:"beans",greenbeans:"beans",mungbean:"mung_bean",
  peanuts:"groundnut",peanut:"groundnut",soya:"soybean",pigeonpea:"pigeon_pea",
  onions:"onion",wmelon:"watermelon",butternuts:"butternut",redkuri:"red_kuri",
  squash:"butternut",pepper:"chili_pepper",chilli:"chili_pepper",chilies:"chili_pepper",
  sweetpotato:"sweet_potato",passionfruit:"passion_fruit",datepalm:"date_palm",
  greenmanure:"green_manure",covercrop:"green_manure",
};
function slug(value){
  return String(value||"").trim().toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_|_$/g,"");
}
function compact(value){ return slug(value).replace(/_/g,""); }
function libraryCrop(raw){
  const key=compact(raw);
  const alias=CROP_ALIASES[key];
  return CROP_LIBRARY.find(function(c){return compact(c.id)===key||compact(c.name)===key||c.id===alias;})||null;
}
function csvRows(text){
  const rows=[]; let row=[], cell="", quoted=false;
  for(let i=0;i<text.length;i+=1){
    const ch=text[i], next=text[i+1];
    if(ch==='"'&&quoted&&next==='"'){cell+='"';i+=1;continue;}
    if(ch==='"'){quoted=!quoted;continue;}
    if(ch===","&&!quoted){row.push(cell.trim());cell="";continue;}
    if((ch==="\n"||ch==="\r")&&!quoted){
      if(ch==="\r"&&next==="\n")i+=1;
      row.push(cell.trim());cell="";
      if(row.some(Boolean))rows.push(row);row=[];continue;
    }
    cell+=ch;
  }
  row.push(cell.trim()); if(row.some(Boolean))rows.push(row);
  return rows;
}
function rotationSlots(){
  const defaultSeasons=["Gu","Deyr","Gu","Deyr","Gu"];
  return defaultSeasons.map(function(season,index){return {key:"y"+(index+1),year:index+1,season,cropId:""};});
}
function defaultRotation(){
  const ids=["maize","cowpea","sorghum","groundnut","sesame"];
  return rotationSlots().map(function(slot,i){return Object.assign({},slot,{cropId:ids[i]});});
}
function normalizedRoot(value,fallback){
  const key=compact(value);
  if(key.includes("deep"))return "Deep";
  if(key.includes("shallow"))return "Shallow";
  if(key.includes("medium"))return "Medium";
  return fallback||"Medium";
}
function normalizedDemand(value,fallback){
  const key=compact(value);
  if(key.includes("fixer")||key.includes("fixing"))return "Nitrogen Fixer";
  if(key.includes("heavy"))return "Heavy Feeder";
  if(key.includes("light"))return "Light Feeder";
  return fallback||"Light Feeder";
}
function maturitySeason(days){
  const value=Number(days)||90;
  if(value<=60)return "Short-cycle relay window";
  if(value<=95)return "Gu / Deyr short-rain window";
  if(value<=150)return "Full primary rainy season";
  if(value<=365)return "Early Gu establishment";
  return "Perennial establishment / irrigated";
}
function seasonList(value,fallback){
  const items=String(value||"").split(/[|;/]+/).map(function(x){return x.trim();}).filter(Boolean);
  return items.length?items:(fallback||["Gu"]);
}
function cropRecord(raw,family,rootDepth,nitrogenDemand,minPh,maxPh,maturityDays,seasons,category){
  const known=libraryCrop(raw);
  const base=known||crop(slug(raw)||"crop_"+Date.now(),String(raw||"").trim(),category||"Imported",family||"Unclassified",
    normalizedRoot(rootDepth),normalizedDemand(nitrogenDemand),5.5,7.5,Number(maturityDays)||90,[maturitySeason(maturityDays)],"#64748b");
  const result=Object.assign({},base,{category:category||base.category,family:family||base.family,
    rootDepth:normalizedRoot(rootDepth,base.rootDepth),nitrogenDemand:normalizedDemand(nitrogenDemand,base.nitrogenDemand),
    minPh:Number.isFinite(minPh)?minPh:base.minPh,maxPh:Number.isFinite(maxPh)?maxPh:base.maxPh,
    maturityDays:Number.isFinite(maturityDays)&&maturityDays>0?Math.round(maturityDays):base.maturityDays,
    seasons:seasonList(seasons,base.seasons)});
  if(result.minPh>result.maxPh){const swap=result.minPh;result.minPh=result.maxPh;result.maxPh=swap;}
  result.pathologies=linkedPathologies(result);
  return result;
}
function parseCropPlan(text){
  const rows=csvRows(text);
  if(!rows.length)throw new Error("The CSV is empty.");
  const headerIndex=rows.findIndex(function(row){return row.some(function(v){return ["crop","cropname","name"].includes(compact(v));});});
  let catalog=[], sequence=[], assignments=[];
  if(headerIndex>=0){
    const headers=rows[headerIndex].map(compact);
    const at=function(names){return headers.findIndex(function(h){return names.includes(h);});};
    const cropAt=at(["crop","cropname","name"]), familyAt=at(["family","cropfamily","botanicalfamily"]);
    const rootAt=at(["rootdepthprofile","rootdepth","rootprofile"]);
    const demandAt=at(["nitrogendemandcategory","nitrogendemand","nutrientdemand","feedercategory"]);
    const minAt=at(["minph","phmin","minimumph","minimumsoilphthreshold"]), maxAt=at(["maxph","phmax","maximumph","maximumsoilphthreshold"]);
    const maturityAt=at(["averagematuritytimeline","averagematuritytimelinedaystoharvest","daystoharvest","maturitydays","maturitytimeline"]);
    const yearAt=at(["year","planyear"]), seasonAt=at(["season","cycle","idealseason","plantingwindow"]), categoryAt=at(["category","croptype"]);
    const data=rows.slice(headerIndex+1).filter(function(row){return row[cropAt]&&row[cropAt].trim();});
    const rawYears=data.map(function(r){return Number(r[yearAt]);}).filter(Number.isFinite);
    const actualYears=Array.from(new Set(rawYears.filter(function(y){return y>5;}))).sort();
    data.forEach(function(row){
      const crop=cropRecord(row[cropAt],row[familyAt],row[rootAt],row[demandAt],parseFloat(row[minAt]),parseFloat(row[maxAt]),
        parseFloat(row[maturityAt]),row[seasonAt],row[categoryAt]);
      catalog.push(crop);sequence.push(crop.id);
      let yr=Number(row[yearAt]);
      if(yr>5)yr=actualYears.indexOf(yr)+1;
      if(yr>=1&&yr<=5){
        const season=String(row[seasonAt]||crop.seasons[0]||"Gu").trim()||"Gu";
        assignments.push({key:"y"+yr,cropId:crop.id,season:season});
      }
    });
  }else{
    const rowSequences=rows.map(function(row){
      const crops=row.map(libraryCrop).filter(Boolean);
      return crops.filter(function(c,i){return i===0||c.id!==crops[i-1].id;});
    }).filter(function(row){return row.length;});
    const best=rowSequences.sort(function(a,b){return b.length-a.length;})[0]||[];
    sequence=best.map(function(c){return c.id;});
    rows.forEach(function(row){row.forEach(function(cell){const crop=libraryCrop(cell);if(crop)catalog.push(crop);});});
  }
  catalog=catalog.filter(function(c,i,all){return all.findIndex(function(x){return x.id===c.id;})===i;});
  if(!catalog.length)throw new Error("No crop names were recognized. Include a 'crop' column or common crop names.");
  const slots=rotationSlots();
  if(assignments.length){assignments.forEach(function(a){const slot=slots.find(function(s){return s.key===a.key;});if(slot){slot.cropId=a.cropId;slot.season=a.season||slot.season;}});}
  let seqAt=0;
  slots.forEach(function(slot){if(!slot.cropId){slot.cropId=(sequence[seqAt%sequence.length]||catalog[seqAt%catalog.length].id);seqAt+=1;}});
  return {catalog,slots,rowCount:rows.length};
}

/* ═════════ UI ATOMS ═════════ */
function iconComponentName(name){
  return String(name||"").split("-").map(function(part){return part.charAt(0).toUpperCase()+part.slice(1);}).join("");
}
function reactSvgAttribute(name){
  if(name==="class")return "className";
  if(name.indexOf("aria-")===0||name.indexOf("data-")===0)return name;
  return name.replace(/-([a-z])/g,function(_,letter){return letter.toUpperCase();});
}
function renderLucideNode(node,key,rootClass){
  if(!node)return null;
  const tag=node[0], raw=node[1]||{}, children=node[2]||[];
  const attrs={key:key};
  Object.keys(raw).forEach(function(name){attrs[reactSvgAttribute(name)]=raw[name];});
  if(rootClass)attrs.className=rootClass;
  if(tag==="svg")attrs["aria-hidden"]="true";
  return e(tag,attrs,children.map(function(child,index){return renderLucideNode(child,key+"-"+index,null);}));
}
function Icon(props){
  const name=iconComponentName(props.name);
  const node=window.lucide&&lucide.icons&&lucide.icons[name];
  return node?renderLucideNode(node,"icon",props.cls||"w-4 h-4"):e("span",{className:props.cls||"w-4 h-4","aria-hidden":"true"});
}
function Panel(props){
  return e("section",{className:"rounded-2xl border border-slate-700/60 bg-slate-900/80 backdrop-blur p-4 shadow-xl "+(props.cls||"")},
    e("div",{className:"flex flex-wrap items-center gap-2 mb-3"},
      e("span",{className:"w-7 h-7 rounded-lg bg-emerald-600/20 text-emerald-300 flex items-center justify-center"},e(Icon,{name:props.icon})),
      e("h2",{className:"font-bold text-slate-100 text-sm tracking-wide"},props.title),
      props.right && e("div",{className:"ml-auto"},props.right)),
    props.children);
}
function EngineerPanel(props){
  return e(Panel,{title:uiText(props.lang||"en","engineer"),icon:"hard-hat",cls:"2xl:col-span-2",
    right:e("span",{className:"text-[10px] text-emerald-300 border border-emerald-700/60 rounded-full px-2 py-1"},"ACTIVE SHIFT")},
    e("div",{className:"grid grid-cols-1 lg:grid-cols-[1fr_1.4fr] gap-3"},
      e("div",{className:"rounded-xl border border-emerald-600/50 bg-emerald-950/40 p-4 flex flex-col sm:flex-row sm:items-center gap-3"},
        e("span",{className:"w-11 h-11 rounded-xl bg-emerald-500/15 text-emerald-300 flex items-center justify-center"},e(Icon,{name:"shield-check",cls:"w-6 h-6"})),
        e("div",null,e("div",{className:"text-[10px] uppercase tracking-widest text-emerald-400"},"Active technical engineer"),
          e("div",{className:"font-bold text-lg text-white"},props.duty.name),
          e("div",{className:"font-mono text-xs text-slate-400"},props.duty.license)),
        e("select",{value:props.duty.id,onChange:function(ev){props.setDutyId(Number(ev.target.value));},
          className:"w-full sm:ml-auto sm:max-w-56 bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-2 text-xs"},
          props.engineers.map(function(g){return e("option",{key:g.id,value:g.id},g.name);}))),
      e("div",{className:"rounded-xl border border-slate-700 bg-slate-800/50 p-3"},
        e("div",{className:"text-[10px] uppercase tracking-widest text-slate-500 mb-2"},"Add engineer to duty roster"),
        e("div",{className:"grid grid-cols-1 sm:grid-cols-[1fr_150px_auto] gap-2"},
          e("input",{value:props.engName,onChange:function(ev){props.setEngName(ev.target.value);},placeholder:"Engineer full name",
            className:"bg-slate-950 border border-slate-700 focus:border-emerald-500 rounded-lg px-3 py-2 text-xs"}),
          e("input",{value:props.engLic,onChange:function(ev){props.setEngLic(ev.target.value);},placeholder:"License ID",
            className:"bg-slate-950 border border-slate-700 focus:border-emerald-500 rounded-lg px-3 py-2 text-xs"}),
          e("button",{onClick:props.addEngineer,disabled:!props.engName.trim()||!props.engLic.trim(),
            className:"rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 px-4 py-2 text-xs font-bold text-white"},
            e("span",{className:"flex items-center justify-center gap-1.5"},e(Icon,{name:"user-plus",cls:"w-3.5 h-3.5"}),"Add & activate"))),
        e("div",{className:"mt-2 text-[10px] text-slate-500"},props.engineers.length+" engineers in local roster · duty changes apply instantly"))));
}
function RotationPlanner(props){
  const lang=props.lang||"en";
  const derivedFields=(props.samples||[]).slice(0,5).map(function(sample,index){
    return {id:sample.id,name:sample.farmer+" · "+sample.location,ph:Number(sample.ph),texture:sample.texture,
      organicMatter:Number(sample.om)||1.2,nitrogenReserve:Math.max(35,72-index*7)};
  });
  const fallbackFields=derivedFields.length?derivedFields:[
    {id:"plot-a",name:"North Demonstration Plot",ph:6.4,texture:"sandy loam",organicMatter:1.5,nitrogenReserve:68},
    {id:"plot-b",name:"River Irrigation Block",ph:7.7,texture:"alluvial silt",organicMatter:1.2,nitrogenReserve:61},
    {id:"plot-c",name:"Upland Trial Field",ph:5.3,texture:"red loam",organicMatter:0.9,nitrogenReserve:48},
  ];
  const [catalog,setCatalog]=useState(function(){
    try{const saved=JSON.parse(localStorage.getItem("lims_strategic_crop_catalog_v5"));return Array.isArray(saved)&&saved.length?saved:CROP_LIBRARY;}catch(_){return CROP_LIBRARY;}
  });
  const [rotation,setRotation]=useState(function(){
    try{const saved=JSON.parse(localStorage.getItem("lims_strategic_rotation_v2"));return Array.isArray(saved)&&saved.length===5?saved:defaultRotation();}catch(_){return defaultRotation();}
  });
  const [fields,setFields]=useState(function(){
    try{const saved=JSON.parse(localStorage.getItem("lims_strategic_fields_v2"));return Array.isArray(saved)&&saved.length?saved:fallbackFields;}catch(_){return fallbackFields;}
  });
  const [fieldId,setFieldId]=useState(function(){return localStorage.getItem("lims_strategic_field_id")||fallbackFields[0].id;});
  const [search,setSearch]=useState("");
  const [categoryFilter,setCategoryFilter]=useState("All categories");
  const [familyFilter,setFamilyFilter]=useState("All families");
  const [demandFilter,setDemandFilter]=useState("All demands");
  const [sortMode,setSortMode]=useState("name");
  const [selectedCropId,setSelectedCropId]=useState("");
  const [linkedPathologyKey,setLinkedPathologyKey]=useState("");
  const [dragOver,setDragOver]=useState("");
  const [importState,setImportState]=useState({kind:"idle",message:"Fallback enterprise catalog active — upload or drop a CSV to replace it."});

  useEffect(function(){localStorage.setItem("lims_strategic_crop_catalog_v5",JSON.stringify(catalog));},[catalog]);
  useEffect(function(){localStorage.setItem("lims_strategic_rotation_v2",JSON.stringify(rotation));},[rotation]);
  useEffect(function(){localStorage.setItem("lims_strategic_fields_v2",JSON.stringify(fields));},[fields]);
  useEffect(function(){localStorage.setItem("lims_strategic_field_id",fieldId);},[fieldId]);
  useEffect(function(){
    if(!window.AGRI_DATA_STORE)return;
    const merge=function(records){const master=new Map(SHARED_AGRI.catalog.map(function(item){return [item.id,item];}));(Array.isArray(records)?records:[]).forEach(function(item){master.set(item.id,item);});const synchronized=Array.from(master.values());setCatalog(function(previous){const map=new Map(previous.map(function(item){return [item.id,item];}));synchronized.map(sharedCropRecord).forEach(function(item){map.set(item.id,item);});return Array.from(map.values()).sort(function(a,b){return a.name.localeCompare(b.name);});});};
    AGRI_DATA_STORE.ready.then(merge).catch(console.warn);return AGRI_DATA_STORE.subscribe(merge);
  },[]);
  useEffect(function(){
    setFields(function(previous){
      const additions=derivedFields.filter(function(field){return !previous.some(function(saved){return saved.id===field.id;});});
      return additions.length?previous.concat(additions):previous;
    });
  },[props.samples]);

  const activeField=fields.find(function(field){return field.id===fieldId;})||fields[0];
  const byId=useMemo(function(){const out={};catalog.forEach(function(crop){out[crop.id]=crop;});return out;},[catalog]);
  const selectedCrop=byId[selectedCropId]||null;
  const selectedPathologies=selectedCrop&&selectedCrop.pathologies?selectedCrop.pathologies:[];
  const selectedPathology=selectedPathologies.find(function(item){return item.disease===linkedPathologyKey;})||selectedPathologies[0]||null;
  const categories=useMemo(function(){return Array.from(new Set(catalog.map(function(crop){return crop.category;}))).sort();},[catalog]);
  const families=useMemo(function(){return Array.from(new Set(catalog.map(function(crop){return crop.family;}))).sort();},[catalog]);
  const filteredCrops=useMemo(function(){
    const query=search.trim().toLowerCase();
    const rows=catalog.filter(function(crop){
      const matchesSearch=!query||(crop.name+" "+crop.family+" "+crop.category+" "+crop.rootDepth+" "+crop.nitrogenDemand).toLowerCase().includes(query);
      return matchesSearch&&(categoryFilter==="All categories"||crop.category===categoryFilter)&&(familyFilter==="All families"||crop.family===familyFilter)&&(demandFilter==="All demands"||crop.nitrogenDemand===demandFilter);
    });
    return rows.sort(function(a,b){
      if(sortMode==="maturity")return a.maturityDays-b.maturityDays;
      if(sortMode==="family")return a.family.localeCompare(b.family)||a.name.localeCompare(b.name);
      return a.name.localeCompare(b.name);
    });
  },[catalog,search,categoryFilter,familyFilter,demandFilter,sortMode]);

  const risks=useMemo(function(){
    const out=[];
    rotation.forEach(function(slot,index){
      const current=byId[slot.cropId]; if(!current)return;
      if(activeField&&(activeField.ph<current.minPh||activeField.ph>current.maxPh))out.push({year:slot.year,key:slot.key,type:"pH",severity:"high",
        message:current.name+" requires pH "+current.minPh+"–"+current.maxPh+"; "+activeField.name+" is pH "+Number(activeField.ph).toFixed(1)+"."});
      const previous=index?byId[rotation[index-1].cropId]:null;
      if(previous&&previous.family===current.family)out.push({year:slot.year,key:slot.key,type:"Family conflict",severity:"high",
        message:previous.name+" and "+current.name+" are both "+current.family+" in back-to-back years."});
      if(previous&&previous.nitrogenDemand==="Heavy Feeder"&&current.nitrogenDemand==="Heavy Feeder")out.push({year:slot.year,key:slot.key,type:"Nutrient depletion",severity:"medium",
        message:"Sequential heavy feeders ("+previous.name+" → "+current.name+") need a nitrogen fixer or fallow year between them."});
    });
    return out;
  },[rotation,byId,activeField]);
  const risksByYear=useMemo(function(){const out={};risks.forEach(function(risk){out[risk.year]=(out[risk.year]||[]).concat(risk);});return out;},[risks]);
  const healthMatrix=useMemo(function(){
    let nitrogen=activeField?Number(activeField.nitrogenReserve)||60:60;
    let previous=null;
    return rotation.map(function(slot){
      const crop=byId[slot.cropId], yearRisks=risksByYear[slot.year]||[];
      if(!crop){nitrogen=Math.min(100,nitrogen+10);previous=null;return {year:slot.year,nitrogen:Math.round(nitrogen),health:Math.min(100,78+slot.year*2),phFit:true,rootMix:true};}
      nitrogen+=crop.nitrogenDemand==="Nitrogen Fixer"?16:crop.nitrogenDemand==="Heavy Feeder"?-18:-7;
      nitrogen=Math.max(5,Math.min(100,nitrogen));
      const phFit=!activeField||(activeField.ph>=crop.minPh&&activeField.ph<=crop.maxPh);
      const rootMix=!previous||previous.rootDepth!==crop.rootDepth;
      const organicBonus=!activeField?0:activeField.organicMatter>=2?6:activeField.organicMatter>=1?2:-5;
      const health=Math.max(10,Math.min(100,82-yearRisks.length*14+(crop.nitrogenDemand==="Nitrogen Fixer"?8:0)+(rootMix?4:-4)+organicBonus));
      previous=crop;return {year:slot.year,nitrogen:Math.round(nitrogen),health:Math.round(health),phFit,rootMix};
    });
  },[rotation,byId,risksByYear,activeField]);
  const forecast=useMemo(function(){
    const selected=rotation.map(function(slot){return byId[slot.cropId];}).filter(Boolean);
    const windows=Array.from(new Set(selected.flatMap(function(crop){return crop.seasons||[];})));
    return {days:selected.reduce(function(sum,crop){return sum+(Number(crop.maturityDays)||0);},0),
      families:new Set(selected.map(function(crop){return crop.family;})).size,windows,
      compliance:Math.max(0,100-risks.filter(function(risk){return risk.severity==="high";}).length*18-risks.filter(function(risk){return risk.severity!=="high";}).length*10)};
  },[rotation,byId,risks]);

  function assignCrop(key,cropId){
    setRotation(function(previous){return previous.map(function(slot){return slot.key===key?Object.assign({},slot,{cropId}):slot;});});
    if(cropId&&byId[cropId]){setSelectedCropId(cropId);setLinkedPathologyKey((byId[cropId].pathologies[0]||{}).disease||"");}
  }
  function setSeason(key,season){setRotation(function(previous){return previous.map(function(slot){return slot.key===key?Object.assign({},slot,{season}):slot;});});}
  function updateField(name,value){setFields(function(previous){return previous.map(function(field){return field.id===fieldId?Object.assign({},field,{[name]:value}):field;});});}
  function autoBalance(){
    const compatible=catalog.filter(function(crop){return !activeField||(activeField.ph>=crop.minPh&&activeField.ph<=crop.maxPh);});
    const choices=compatible.length?compatible:catalog; let previous=null,cursor=0;
    const next=rotationSlots().map(function(slot,index){
      slot.season=(rotation[index]&&rotation[index].season)||slot.season;
      let candidate=choices[cursor%choices.length];
      for(let tries=0;tries<choices.length;tries+=1){
        const familySafe=!previous||candidate.family!==previous.family;
        const nutrientSafe=!previous||previous.nitrogenDemand!=="Heavy Feeder"||candidate.nitrogenDemand!=="Heavy Feeder";
        if(familySafe&&nutrientSafe)break;
        cursor+=1;candidate=choices[cursor%choices.length];
      }
      cursor+=1;previous=candidate;slot.cropId=candidate.id;return slot;
    });
    setRotation(next);setImportState({kind:"ok",message:"Auto-balanced against pH, family and nitrogen-demand rules."});
  }
  async function importFile(file){
    if(!file)return;
    setImportState({kind:"loading",message:"Parsing and validating "+file.name+"…"});
    try{
      const result=parseCropPlan(await file.text());
      setCatalog(result.catalog);setRotation(result.slots);setSelectedCropId("");
      if(window.AGRI_DATA_STORE){const sharedRecords=result.catalog.map(function(item){return Object.assign({},item,{category:item.category==="Fruit"?"Fruits":item.category==="Vegetable"?"Vegetables":item.category,categorySo:item.category==="Fruit"?"Midho":item.category==="Vegetable"?"Khudaar":item.categorySo||item.category,catalogSource:"lims-csv"});});AGRI_DATA_STORE.upsertMany(sharedRecords).catch(console.warn);}
      setImportState({kind:"ok",message:"Mapped "+result.catalog.length+" crop rules from "+result.rowCount+" CSV rows and synchronized them to GIS."});
    }catch(error){setImportState({kind:"error",message:error.message||"Unable to parse this CSV."});}
  }
  function handleFileInput(event){const file=event.target.files&&event.target.files[0];importFile(file);event.target.value="";}
  function handleFileDrop(event){event.preventDefault();importFile(event.dataTransfer.files&&event.dataTransfer.files[0]);}
  function downloadTemplate(){
    const content=["Crop Name,Botanical Family,Root Depth Profile,Nitrogen Demand Category,Minimum Soil pH Threshold,Maximum Soil pH Threshold,Average Maturity Timeline (Days to Harvest),Ideal Season,Year",
      "Maize,Poaceae,Medium,Heavy Feeder,5.5,7.5,90,Gu,1","Cowpea,Fabaceae,Deep,Nitrogen Fixer,5.5,7.5,75,Deyr,2","Tomato,Solanaceae,Deep,Heavy Feeder,5.5,7.5,100,Irrigated Jilaal,3"].join("\r\n");
    const link=document.createElement("a");link.href=URL.createObjectURL(new Blob([content],{type:"text/csv"}));link.download="strategic-crop-plan-template.csv";
    document.body.appendChild(link);link.click();link.remove();URL.revokeObjectURL(link.href);
  }
  function dropCrop(event,key){event.preventDefault();const cropId=event.dataTransfer.getData("text/crop-id");if(cropId)assignCrop(key,cropId);setDragOver("");}

  return e(Panel,{title:uiText(lang,"planner"),icon:"calendar-range",cls:"strategic-planner 2xl:col-span-2",
    right:e("span",{className:"text-[10px] text-slate-500"},catalog.length+" crop rules · drag, drop or select")},
    e("div",{className:"grid grid-cols-1 xl:grid-cols-[300px_minmax(0,1fr)] gap-4"},
      e("aside",{className:"rounded-xl border border-slate-700 bg-slate-950/70 p-3"},
        e("div",{onDragOver:function(event){event.preventDefault();},onDrop:handleFileDrop,
          className:"rounded-xl border border-dashed border-emerald-700/70 bg-emerald-950/20 p-3 text-center"},
          e(Icon,{name:"file-up",cls:"w-5 h-5 text-emerald-300 mx-auto"}),
          e("div",{className:"mt-1 text-xs font-bold"},"CSV rules importer"),
          e("div",{className:"text-[10px] text-slate-500"},"Drop a multi-column CSV here or choose a file"),
          e("label",{className:"inline-flex mt-2 cursor-pointer rounded-lg bg-emerald-600 hover:bg-emerald-500 px-3 py-1.5 text-[10px] font-bold text-white"},"Choose CSV",
            e("input",{type:"file",accept:".csv,text/csv",onChange:handleFileInput,className:"hidden"})),
          e("button",{onClick:downloadTemplate,className:"ml-2 rounded-lg border border-slate-700 hover:border-emerald-500 px-2 py-1.5 text-[10px] text-slate-300"},"Download template")),
        e("div",{className:"mt-2 text-[10px] "+(importState.kind==="error"?"text-red-300":importState.kind==="ok"?"text-emerald-300":"text-slate-500")},importState.message),
        e("div",{className:"relative mt-3"},e(Icon,{name:"search",cls:"absolute left-2.5 top-2.5 w-3.5 h-3.5 text-slate-500"}),
          e("input",{value:search,onChange:function(event){setSearch(event.target.value);},placeholder:"Search crop, family or category…",
            className:"w-full bg-slate-900 border border-slate-700 rounded-lg pl-8 pr-2 py-2 text-xs"})),
        e("div",{className:"grid grid-cols-2 gap-1.5 mt-2"},
          e("select",{value:categoryFilter,onChange:function(event){setCategoryFilter(event.target.value);},className:"col-span-2 bg-slate-900 border border-slate-700 rounded-lg px-2 py-1.5 text-[10px]"},
            e("option",null,"All categories"),categories.map(function(category){const label=category==="Seed Oil"?uiText(lang,"seedOil"):category==="Fruit"?uiText(lang,"fruits"):category==="Vegetable"?uiText(lang,"vegetables"):category;return e("option",{key:category,value:category},label);})),
          e("select",{value:familyFilter,onChange:function(event){setFamilyFilter(event.target.value);},className:"bg-slate-900 border border-slate-700 rounded-lg px-2 py-1.5 text-[10px]"},
            e("option",null,"All families"),families.map(function(family){return e("option",{key:family,value:family},family);})),
          e("select",{value:demandFilter,onChange:function(event){setDemandFilter(event.target.value);},className:"bg-slate-900 border border-slate-700 rounded-lg px-2 py-1.5 text-[10px]"},
            ["All demands","Heavy Feeder","Light Feeder","Nitrogen Fixer"].map(function(value){return e("option",{key:value,value},value);})),
          e("select",{value:sortMode,onChange:function(event){setSortMode(event.target.value);},className:"col-span-2 bg-slate-900 border border-slate-700 rounded-lg px-2 py-1.5 text-[10px]"},
            e("option",{value:"name"},"Sort: Crop name"),e("option",{value:"family"},"Sort: Botanical family"),e("option",{value:"maturity"},"Sort: Fastest maturity"))),
        e("div",{className:"mt-2 flex items-center justify-between text-[10px] text-slate-500"},
          e("span",null,"Showing "+Math.min(filteredCrops.length,120)+" of "+filteredCrops.length),e("span",null,catalog.filter(function(c){return c.category==="Vegetable";}).length+" "+uiText(lang,"vegetables")+" · "+catalog.filter(function(c){return c.category==="Fruit";}).length+" "+uiText(lang,"fruits")+" · "+catalog.filter(function(c){return c.category==="Seed Oil";}).length+" seed oils")),
        e("div",{className:"mt-2 max-h-[38rem] overflow-y-auto space-y-1.5 pr-1"},filteredCrops.slice(0,120).map(function(crop){
          const selected=selectedCropId===crop.id;
          return e("button",{key:crop.id,draggable:true,onDragStart:function(event){event.dataTransfer.setData("text/crop-id",crop.id);event.dataTransfer.effectAllowed="copy";},
            onClick:function(){if(selected){setSelectedCropId("");setLinkedPathologyKey("");}else{setSelectedCropId(crop.id);setLinkedPathologyKey((crop.pathologies[0]||{}).disease||"");}},
            className:"w-full rounded-lg border p-2 text-left transition "+(selected?"border-emerald-500 bg-emerald-950/30":"border-slate-800 bg-slate-900/70 hover:border-slate-600")},
            e("div",{className:"flex items-center gap-2"},e("span",{className:"w-2.5 h-2.5 rounded-full",style:{backgroundColor:crop.color}}),
              e("b",{className:"text-xs"},crop.name),e("span",{className:"ml-auto text-[9px] text-slate-500"},crop.maturityDays+" d")),
            e("div",{className:"mt-1 text-[9px] text-slate-500"},crop.category+" · "+crop.family+" · "+crop.rootDepth+" root"),
            e("div",{className:"mt-1 flex flex-wrap gap-1"},
              e("span",{className:"rounded-full border border-slate-700 px-1.5 py-0.5 text-[8px] "+(crop.nitrogenDemand==="Nitrogen Fixer"?"text-emerald-300":crop.nitrogenDemand==="Heavy Feeder"?"text-amber-300":"text-sky-300")},crop.nitrogenDemand),
              e("span",{className:"rounded-full border border-slate-700 px-1.5 py-0.5 text-[8px] text-slate-400"},"pH "+crop.minPh+"–"+crop.maxPh)));
        }))),
      e("div",null,
        e("div",{className:"rounded-xl border border-slate-700 bg-slate-950/70 p-3"},
          e("div",{className:"grid grid-cols-1 md:grid-cols-[1.2fr_110px_110px_110px_auto] gap-2 items-end"},
            e("label",{className:"text-[9px] uppercase tracking-widest text-slate-500"},"Active plot / LIMS profile",
              e("select",{value:activeField.id,onChange:function(event){setFieldId(event.target.value);},className:"mt-1 w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-2 text-xs"},
                fields.map(function(field){return e("option",{key:field.id,value:field.id},field.name);}))),
            e("label",{className:"text-[9px] uppercase tracking-widest text-slate-500"},uiText(lang,"soil")+" pH",
              e("input",{value:activeField.ph,type:"number",step:"0.1",min:"3",max:"11",onChange:function(event){updateField("ph",Number(event.target.value));},className:"mt-1 w-full bg-slate-900 border border-slate-700 rounded-lg px-2 py-2 text-xs"})),
            e("label",{className:"text-[9px] uppercase tracking-widest text-slate-500"},"Organic matter %",
              e("input",{value:activeField.organicMatter,type:"number",step:"0.1",min:"0",onChange:function(event){updateField("organicMatter",Number(event.target.value));},className:"mt-1 w-full bg-slate-900 border border-slate-700 rounded-lg px-2 py-2 text-xs"})),
            e("label",{className:"text-[9px] uppercase tracking-widest text-slate-500"},"N reserve %",
              e("input",{value:activeField.nitrogenReserve,type:"number",step:"1",min:"0",max:"100",onChange:function(event){updateField("nitrogenReserve",Number(event.target.value));},className:"mt-1 w-full bg-slate-900 border border-slate-700 rounded-lg px-2 py-2 text-xs"})),
            e("button",{onClick:autoBalance,className:"rounded-lg bg-emerald-600 hover:bg-emerald-500 px-3 py-2 text-xs font-bold text-white flex justify-center items-center gap-1.5"},e(Icon,{name:"sparkles",cls:"w-3.5 h-3.5"}),"Optimize")),
          e("div",{className:"mt-2 text-[10px] text-slate-500"},"Texture: "+activeField.texture+" · profile inherited from the LIMS sample ledger and editable for scenario planning.")),
        e("div",{className:"mt-3 grid grid-cols-2 lg:grid-cols-4 gap-2"},
          [["Lifecycle days",forecast.days.toLocaleString(),"timer"],["Family diversity",forecast.families+" unique","network"],["Compliance",forecast.compliance+"%","shield-check"],["Planting windows",forecast.windows.length,"calendar-clock"]]
            .map(function(card){return e("div",{key:card[0],className:"rounded-xl border border-slate-700 bg-slate-900/70 p-3"},
              e("div",{className:"text-[9px] uppercase tracking-widest text-slate-500 flex items-center gap-1"},e(Icon,{name:card[2],cls:"w-3 h-3"}),card[0]),
              e("div",{className:"mt-1 text-lg font-bold text-slate-100"},card[1]));})),
        e("div",{className:"mt-2 rounded-lg border border-slate-700 bg-slate-900/50 px-3 py-2 text-[10px] text-slate-400"},
          e("b",{className:"text-sky-300"},"Ideal season forecast: "),forecast.windows.length?forecast.windows.join(" · "):"Assign crops to calculate planting windows."),
        selectedCropId&&e("div",{className:"mt-2 rounded-lg border border-emerald-700/50 bg-emerald-950/20 px-3 py-2 text-[10px] text-emerald-200"},
          "Selected ",e("b",null,selectedCrop?selectedCrop.name:"crop")," — click Assign on a year card or drag it into the timeline."),
        selectedCrop&&selectedPathology&&e("div",{className:"mt-2 rounded-xl border border-violet-700/60 bg-violet-950/20 p-3"},
          e("div",{className:"text-[10px] uppercase tracking-widest text-violet-300 font-bold"},"Associated pathology selection · "+selectedCrop.name),
          e("select",{value:selectedPathology.disease,onChange:function(event){setLinkedPathologyKey(event.target.value);},className:"mt-2 w-full rounded-lg border border-violet-700/60 bg-slate-950 px-3 py-2 text-xs"},
            selectedPathologies.map(function(item){return e("option",{key:item.disease,value:item.disease},item.disease);})),
          e("div",{className:"mt-2 grid grid-cols-1 md:grid-cols-2 gap-2 text-[10px]"},
            e("div",{className:"rounded-lg border border-slate-700 bg-slate-900/70 p-2"},e("b",{className:"text-red-300"},"Cause · "),selectedPathology.cause,
              e("div",{className:"mt-1 text-slate-400"},(selectedPathology.symptoms||[]).join(" · "))),
            e("div",{className:"rounded-lg border border-slate-700 bg-slate-900/70 p-2"},e("b",{className:"text-emerald-300"},"Response · "),selectedPathology.remedy||selectedPathology.action)),
        ),
        e("datalist",{id:"rotation-season-options"},SEASON_SUGGESTIONS.map(function(season){return e("option",{key:season,value:season});})),
        e("div",{className:"mt-3 overflow-x-auto pb-2"},
          e("div",{className:"min-w-[900px] grid grid-cols-5 gap-2"},rotation.map(function(slot){
            const crop=byId[slot.cropId],yearRisks=risksByYear[slot.year]||[],isOver=dragOver===slot.key;
            return e("div",{key:slot.key,onDragOver:function(event){event.preventDefault();setDragOver(slot.key);},onDragLeave:function(){setDragOver("");},onDrop:function(event){dropCrop(event,slot.key);},
              className:"relative rounded-xl border p-2 transition "+(isOver?"border-emerald-400 bg-emerald-950/40 scale-[1.01]":yearRisks.length?"border-amber-700/70 bg-amber-950/15":"border-slate-700 bg-slate-950/70")},
              e("div",{className:"h-1 rounded-full mb-2",style:{backgroundColor:crop?crop.color:"#334155"}}),
              e("div",{className:"flex items-center justify-between"},e("b",{className:"text-xs"},"Year "+slot.year),
                e("span",{className:"text-[9px] "+(yearRisks.length?"text-amber-300":"text-emerald-400")},yearRisks.length?yearRisks.length+" alert"+(yearRisks.length>1?"s":""):"compliant")),
              e("label",{className:"block mt-2 text-[8px] uppercase tracking-widest text-slate-500"},"Planting season",
                e("input",{value:slot.season,list:"rotation-season-options",onChange:function(event){setSeason(slot.key,event.target.value);},className:"mt-0.5 w-full bg-slate-900 border border-slate-700 rounded px-1.5 py-1 text-[10px] normal-case tracking-normal"})),
              e("select",{value:slot.cropId,onChange:function(event){assignCrop(slot.key,event.target.value);},className:"mt-2 w-full bg-slate-900 border border-slate-700 rounded-lg px-2 py-2 text-xs"},
                e("option",{value:""},"— Fallow year —"),catalog.map(function(item){return e("option",{key:item.id,value:item.id},item.name);})),
              crop?e("div",{className:"mt-2"},
                e("div",{className:"font-bold text-sm",style:{color:crop.color}},crop.name),
                e("div",{className:"text-[9px] text-slate-500"},crop.family+" · "+crop.rootDepth+" root · "+crop.maturityDays+" days"),
                e("span",{className:"inline-block mt-1 rounded-full border border-slate-700 px-1.5 py-0.5 text-[8px]"},crop.nitrogenDemand))
                :e("div",{className:"mt-2 min-h-12 border border-dashed border-slate-800 rounded-lg grid place-items-center text-[9px] text-slate-600"},"Drop crop or leave fallow"),
              e("div",{className:"mt-2 flex gap-1"},
                selectedCropId&&e("button",{onClick:function(){assignCrop(slot.key,selectedCropId);},className:"flex-1 rounded bg-emerald-700 hover:bg-emerald-600 px-1.5 py-1 text-[9px] text-white"},"Assign selected"),
                slot.cropId&&e("button",{onClick:function(){assignCrop(slot.key,"");},className:"rounded border border-slate-700 hover:border-red-500 px-1.5 py-1 text-[9px] text-slate-400"},"Clear")));
          }))),
        e("div",{className:"mt-3"},
          e("div",{className:"text-[10px] uppercase tracking-widest text-slate-500 mb-1.5"},"Field Health Matrix · projected decision-support index"),
          e("div",{className:"grid grid-cols-1 sm:grid-cols-5 gap-2"},healthMatrix.map(function(item){return e("div",{key:item.year,className:"rounded-lg border border-slate-700 bg-slate-900/70 p-2"},
            e("div",{className:"flex justify-between text-[9px]"},e("b",null,"Year "+item.year),e("span",{className:item.health>=70?"text-emerald-300":item.health>=45?"text-amber-300":"text-red-300"},item.health+"/100")),
            e("div",{className:"mt-1 text-[8px] text-slate-500"},"Nitrogen reserve "+item.nitrogen+"%"),
            e("div",{className:"mt-1 h-1.5 rounded-full bg-slate-800 overflow-hidden"},e("div",{className:"h-full "+(item.nitrogen>=60?"bg-emerald-500":item.nitrogen>=35?"bg-amber-500":"bg-red-500"),style:{width:item.nitrogen+"%"}})),
            e("div",{className:"mt-1.5 flex flex-wrap gap-1 text-[7px]"},
              e("span",{className:"rounded border px-1 py-0.5 "+(item.phFit?"border-emerald-700 text-emerald-300":"border-red-700 text-red-300")},item.phFit?"pH fit":"pH mismatch"),
              e("span",{className:"rounded border px-1 py-0.5 "+(item.rootMix?"border-sky-700 text-sky-300":"border-amber-700 text-amber-300")},item.rootMix?"root diversity":"same root depth")));
          }))),
        e("div",{className:"mt-3 rounded-xl border p-3 "+(risks.length?"border-amber-700/70 bg-amber-950/15":"border-emerald-700/60 bg-emerald-950/20")},
          e("div",{className:"flex items-center gap-2"},e(Icon,{name:risks.length?"triangle-alert":"badge-check",cls:"w-4 h-4 "+(risks.length?"text-amber-300":"text-emerald-300")}),
            e("b",{className:"text-xs"},risks.length?risks.length+" active agronomic risk"+(risks.length>1?"s":""):"Plan passes all active compliance rules")),
          risks.length?e("div",{className:"mt-2 max-h-36 overflow-y-auto space-y-1.5"},risks.map(function(risk,index){return e("div",{key:risk.key+"-"+risk.type+"-"+index,className:"rounded-lg border border-slate-700 bg-slate-950/60 px-2.5 py-2 text-[10px]"},
            e("span",{className:"mr-2 rounded-full px-1.5 py-0.5 "+(risk.type==="pH"?"bg-violet-900/50 text-violet-200":risk.type==="Family conflict"?"bg-red-900/50 text-red-200":"bg-amber-900/50 text-amber-200")},risk.type),risk.message);}))
            :e("div",{className:"mt-1 text-[10px] text-emerald-200"},"Botanical families, feeder sequence and pH compatibility are compliant."))
      )
    )
  );
}

/* ═════════ CERTIFICATE MODAL (Module 2) ═════════ */
function Certificate(props){
  const sample = props.sample;
  const v = phVerdict(sample.ph);
  useEffect(function(){ props.onIssued(); },[]);
  return e("div",{className:"fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4", role:"dialog","aria-modal":"true"},
    e("div",{className:"cert-wrap bg-white text-slate-900 rounded-2xl shadow-2xl max-w-xl w-full max-h-[92vh] overflow-y-auto"},
      e("div",{className:"p-8"},
        e("div",{className:"border-b-2 border-emerald-700 pb-3 mb-4 flex items-center justify-between"},
          e("div",null,
            e("div",{className:"text-xl font-bold text-emerald-800 tracking-wide"},"SOMALI SPATIALBIO ENGINE"),
            e("div",{className:"text-[11px] tracking-widest text-slate-500 uppercase"},"Official Soil Analysis Certificate")),
          e("svg",{viewBox:"0 0 120 120",className:"w-20 h-20 seal"},
            e("defs",null,e("path",{id:"sa",d:"M60,60 m-45,0 a45,45 0 1,1 90,0 a45,45 0 1,1 -90,0"})),
            e("circle",{cx:60,cy:60,r:56,fill:"none",stroke:"#047857",strokeWidth:2.2}),
            e("circle",{cx:60,cy:60,r:50,fill:"none",stroke:"#047857",strokeWidth:.8,strokeDasharray:"3 3"}),
            e("text",{fontSize:9,fill:"#047857",letterSpacing:2,fontFamily:"Arial"},
              e("textPath",{href:"#sa"},"SOMALI SPATIALBIO ENGINE \u2022 LAB CERTIFIED \u2022")),
            e("text",{x:60,y:62,textAnchor:"middle",fontSize:24,fill:"#047857"},"\u2714"),
            e("text",{x:60,y:78,textAnchor:"middle",fontSize:8,fill:"#047857",fontFamily:"monospace"},sample.id))),
        e("table",{className:"w-full text-sm"},
          e("tbody",null,[
            ["Sample Reference", "#"+sample.id],
            ["Client / Farmer", sample.farmer],
            ["Farm Location", sample.location+" — "+sample.texture],
            ["Test Tier", sample.tier],
            ["Date & Time", today.toDateString()+" · "+sample.time],
            ["Analyzing Engineer", sample.engineer],
          ].map(function(row,i){return e("tr",{key:row[0],className:i<5?"border-b border-slate-200":""},
            e("td",{className:"py-2 text-slate-500 w-40"},row[0]),e("td",{className:"py-2 font-semibold"},row[1]));}))),
        e("div",{className:"mt-4 grid grid-cols-3 gap-2 text-center"},
          [["Soil pH",sample.ph,"text-amber-600"],["EC dS/m",sample.ec,"text-sky-600"],["Organic %",sample.om,"text-emerald-600"]]
          .map(function(c){return e("div",{key:c[0],className:"rounded-lg bg-slate-100 p-2.5"},
            e("div",{className:"text-[10px] uppercase text-slate-500"},c[0]),
            e("div",{className:"text-2xl font-mono font-bold "+c[2]},c[1]));})),
        e("div",{className:"mt-4 rounded-lg border-2 p-3 " + (v.status==="Critically Acidic"?"border-red-300 bg-red-50":v.status==="Mildly Acidic"?"border-amber-300 bg-amber-50":v.status==="Alkaline"?"border-sky-300 bg-sky-50":"border-emerald-300 bg-emerald-50")},
          e("div",{className:"text-[10px] uppercase tracking-widest text-slate-500"},"Chemical status"),
          e("div",{className:"font-bold text-lg "+v.color.replace("300","700")},v.status),
          e("div",{className:"mt-1 text-sm text-slate-700"},"\u2697 "+v.rec)),
        e("div",{className:"mt-6 flex justify-between text-xs text-slate-500"},
          e("span",null,"Analyst: ____________________"),
          e("span",null,"Supervisor: __________________")),
        e("div",{className:"mt-4 pt-3 border-t border-slate-200 text-[10px] text-slate-400 text-center"},
          "Laboratory decision-support output — Somali SpatialBio Engine \u00B7 "+today.getFullYear())),
      e("div",{className:"flex gap-2 p-4 border-t bg-slate-50 rounded-b-2xl"},
        e("button",{onClick:function(){window.print();},className:"flex-1 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-sm"},"\uD83D\uDAF6 Print certificate"),
        e("button",{onClick:props.onClose,className:"px-4 py-2 rounded-lg bg-slate-200 text-sm"},"Close"))));
}

/* ═════════ MAIN APP ═════════ */
function App(){
  const [spectrum, setSpectrum] = useState(function(){const saved=localStorage.getItem("lims_spectrum");return SPECTRUM.some(function(s){return s.id===saved;})?saved:"slate";});
  const [lang,setLang]=useState(function(){return localStorage.getItem("agri_lang")==="so"?"so":"en";});
  const [spectrumOpen, setSpectrumOpen] = useState(false);
  const [engineers, setEngineers] = useState(function(){return JSON.parse(localStorage.getItem("lims_engineers")||"null")||ENGINEERS;});
  const [dutyId, setDutyId] = useState(function(){return parseInt(localStorage.getItem("lims_duty")||"1");});
  const duty = engineers.find(function(x){return x.id===dutyId;})||engineers[0];
  const firstEng = engineers[0].name+" — "+engineers[0].license;
  const [samples, setSamples] = useState(function(){return seedSamples(firstEng);});
  const [invoices, setInvoices] = useState(function(){return seedInvoices(samples);});
  const [month, setMonth] = useState(seedMonth);
  const [revenue, setRevenue] = useState(function(){return seedRevenue(seedInvoices(samples));});
  const [openCert, setOpenCert] = useState(null);
  const [issued, setIssued] = useState(0);
  const [engName, setEngName] = useState(""); const [engLic, setEngLic] = useState("");
  const [payName, setPayName] = useState(""); const [payTier, setPayTier] = useState("Basic pH Test");
  const [payBase, setPayBase] = useState("25"); const [payPaid, setPayPaid] = useState("");
  const [payGw, setPayGw] = useState("ZAAD");
  const [isSampleIds] = useState(new Set());
  /* Module 6 state — Option-2 asynchronous dictionary engine */
  const [diseases, setDiseases] = useState(null);          /* null = still loading (mock API) */
  const [catTab, setCatTab] = useState("All");
  const [disSearch, setDisSearch] = useState("");
  const [selHost, setSelHost] = useState(null);
  const [manifest, setManifest] = useState(null);
  const [issueClient, setIssueClient] = useState(FARMERS[0][0]);
  const [issueDisease, setIssueDisease] = useState("");
  const [issueFeed, setIssueFeed] = useState([]);

  useEffect(function(){ localStorage.setItem("lims_spectrum",spectrum); },[spectrum]);
  useEffect(function(){localStorage.setItem("agri_lang",lang);if(window.AGRI_I18N)AGRI_I18N.setLanguage(lang);},[lang]);
  useEffect(function(){ localStorage.setItem("lims_engineers",JSON.stringify(engineers)); },[engineers]);
  useEffect(function(){ localStorage.setItem("lims_duty",String(duty.id)); },[duty.id]);

  /* Mock asynchronous repository; cancellation avoids updates after unmount. */
  useEffect(function(){
    let active=true;
    loadDiseaseDictionary().then(function(records){if(active)setDiseases(records);});
    return function(){active=false;};
  },[]);

  const diseaseFiltered = useMemo(function(){
    if(!diseases) return [];
    const q=disSearch.trim().toLowerCase();
    return diseases.filter(function(d){
      if(catTab!=="All"&&d.cat!==catTab) return false;
      if(!q) return true;
      const hay=(d.plant+" "+d.disease+" "+d.cause+" "+d.symptoms.join(" ")+" "+d.remedy).toLowerCase();
      return hay.indexOf(q)>=0;
    });
  },[diseases,catTab,disSearch]);

  const catCounts = useMemo(function(){
    const m={All:(diseases||[]).length};
    DISEASE_CATEGORIES.slice(1).forEach(function(c){ m[c]=0; });
    (diseases||[]).forEach(function(d){ m[d.cat]=(m[d.cat]||0)+1; });
    return m;
  },[diseases]);

  const hostGroups = useMemo(function(){
    const m={};
    diseaseFiltered.forEach(function(d){
      if(!m[d.plant]) m[d.plant]={plant:d.plant,cat:d.cat,items:[]};
      m[d.plant].items.push(d);
    });
    return Object.keys(m).map(function(k){ return m[k]; });
  },[diseaseFiltered]);

  /* prune selections that the current filter set no longer contains */
  useEffect(function(){
    if(selHost && hostGroups.every(function(g){ return g.plant!==selHost; })) setSelHost(null);
    if(issueDisease && diseaseFiltered.every(function(d){ return (d.disease+"|"+d.plant)!==issueDisease; })) setIssueDisease("");
  });

  const totals = useMemo(function(){return {
    tested: samples.length, certs: issued,
    avgTAT: (samples.reduce(function(a,s){return a+s.turnaround;},0)/samples.length).toFixed(1)+" h",
    collected: invoices.reduce(function(a,v){return a+v.paid;},0),
    pending: invoices.reduce(function(a,v){return a+v.balance;},0),
  };},[samples,invoices,issued]);

  function addEngineer(){
    if(!engName.trim()||!engLic.trim())return;
    const ne={id:Date.now(),name:engName.trim(),license:engLic.trim()};
    setEngineers(engineers.concat([ne])); setEngName(""); setEngLic(""); setDutyId(ne.id);
  }

  /* payment intake — typed amounts */
  const baseNum = parseFloat(payBase)||0;
  const paidNum = payPaid===""?null:parseFloat(payPaid);
  const live = calcInvoice(baseNum);
  const liveBalance = paidNum==null?live.total:Math.max(0, live.total-paidNum);
  const liveCredit  = paidNum==null?0:Math.max(0, paidNum-live.total);
  function pickTier(t){ setPayTier(t); setPayBase(String(TIERS[t])); }
  function receivePay(){
    if(!payName.trim()||baseNum<=0)return;
    const c = calcInvoice(baseNum);
    const paid = paidNum==null?0:Math.max(0,paidNum);
    const inv={ id:"INV-2026-"+String(101+invoices.length), farmer:payName.trim(), tier:payTier,
      base:baseNum, gw:payGw, subtotal:c.subtotal, total:c.total,
      paid:paid, balance:Math.max(0,c.total-paid), currency:"USD",
      status:invStatus(c.total,paid),
      method:payGw+"-AUTO-"+Math.floor(Math.random()*89999+10000),
      at:new Date().toTimeString().slice(0,5), engineer:duty.name+" — "+duty.license };
    setInvoices(invoices.concat([inv]));
    setRevenue(function(prev){return prev.map(function(r){return r.month==="Aug"
      ? {month:r.month, collected:r.collected+inv.paid, pending:r.pending+inv.balance} : r;});});
    setPayName(""); setPayPaid("");
  }
  function settleInvoice(id){
    setInvoices(invoices.map(function(v){
      if(v.id!==id)return v;
      const newPaid=v.total;
      setRevenue(function(prev){return prev.map(function(r){return r.month==="Aug"
        ? {month:r.month, collected:r.collected+(v.total-v.paid), pending:Math.max(0,r.pending-v.balance)} : r;});});
      return Object.assign({},v,{paid:newPaid,balance:0,status:"PAID"});
    }));
  }
  function registerSample(){
    const ph=parseFloat(document.getElementById("s-ph").value);
    const nm=document.getElementById("s-name").value, lc=document.getElementById("s-loc").value;
    const tr=document.getElementById("s-tier").value;
    if(!nm.trim()||!lc.trim()||isNaN(ph)||ph<3||ph>14)return;
    const s={ id:"SMP-"+String(100+samples.length+1).slice(-3),
      farmer:nm.trim(), location:lc.trim(), texture:"field sample", tier:tr,
      ph:Math.round(ph*10)/10, ec:"—", om:"—",
      time:new Date().toTimeString().slice(0,5), turnaround:2.5,
      engineer:duty.name+" — "+duty.license, currency:"USD" };
    setSamples(samples.concat([s]));
    setMonth(function(m){return m.map(function(r){return r.day===today.getDate()?Object.assign({},r,{samples:r.samples+1}):r;});});
    document.getElementById("s-name").value="";document.getElementById("s-loc").value="";document.getElementById("s-ph").value="";
  }
  function appendIssue(rec){
    if(!rec||!issueClient.trim())return;
    const entry={ t:new Date().toTimeString().slice(0,5), client:issueClient,
      plant:rec.plant, disease:rec.disease, cat:rec.cat };
    setIssueFeed(function(f){ return [entry].concat(f).slice(0,12); });
  }
  function logIssue(){
    if(!issueDisease)return;
    const parts=issueDisease.split("|");
    appendIssue((diseases||[]).filter(function(d){ return d.disease===parts[0]&&d.plant===parts[1]; })[0]);
  }

  const themeCls = (SPECTRUM.find(function(s){return s.id===spectrum;})||{}).cls || "bg-slate-950";

  return e("div",{className:themeCls+" min-h-screen text-slate-100 transition-colors duration-500"},
    /* ── HEADER ── */
    e("header",{className:"sticky top-0 z-40 border-b border-slate-700/60 bg-black/30 backdrop-blur px-3 sm:px-4 min-h-14 py-2 flex flex-wrap items-center gap-2 sm:gap-3"},
      e("div",{className:"font-extrabold tracking-widest text-xs sm:text-sm"},
        e("span",{className:"text-emerald-400"},"SOMALI "),e("span",null,"SPATIALBIO "),e("span",{className:"text-sky-400"},"ENGINE"),
        e("span",{className:"hidden sm:inline text-slate-400 font-normal ml-2 text-xs"},"· LabOps LIMS")),
      e("a",{href:GIS_ENGINE_URL,title:"Open GIS Engine",className:"text-xs px-2.5 py-1.5 rounded-lg border border-slate-600 hover:border-emerald-500 text-slate-300 flex items-center gap-1"},e(Icon,{name:"map",cls:"w-3.5 h-3.5"}),e("span",{className:"hidden sm:inline"},"GIS Engine")),
      e("div",{className:"flex-1"}),
      e("div",{className:"hidden md:flex items-center gap-2 rounded-full border border-emerald-600/50 bg-emerald-900/30 px-3 py-1.5"},
        e("span",{className:"relative flex h-2 w-2"},
          e("span",{className:"animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"}),
          e("span",{className:"relative inline-flex rounded-full h-2 w-2 bg-emerald-400"})),
        e("span",{className:"text-xs"},lang==="so"?"Shaqada: ":"On duty: ",e("b",null,duty.name), e("span",{className:"text-slate-400 font-mono text-[10px] ml-1"},duty.license))),
      e("button",{onClick:function(){setLang(lang==="en"?"so":"en");},title:"Soomaali | English",className:"min-w-[168px] whitespace-nowrap rounded-lg border border-emerald-700/70 bg-emerald-950/30 px-4 py-2 text-sm font-black text-emerald-200"},
        e("span",{className:lang==="so"?"text-white":"text-slate-500"},"Soomaali")," | ",e("span",{className:lang==="en"?"text-white":"text-slate-500"},"English")),
      e("div",{className:"relative"},
        e("button",{onClick:function(){setSpectrumOpen(!spectrumOpen);},"aria-label":"Background spectrum","aria-expanded":spectrumOpen,
          className:"p-2 rounded-lg border border-slate-600 hover:border-emerald-500"},e(Icon,{name:"palette"})),
        spectrumOpen && e("div",{className:"absolute right-0 mt-2 w-52 rounded-xl border border-slate-600 bg-slate-900 shadow-2xl p-2 z-50"},
          e("div",{className:"text-[10px] uppercase tracking-widest text-slate-500 px-1 pb-1.5"},"Background spectrum"),
          SPECTRUM.map(function(s){return e("button",{key:s.id,onClick:function(){setSpectrum(s.id);setSpectrumOpen(false);},
            className:"w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs text-left hover:bg-slate-800 "+(s.id===spectrum?"text-emerald-300":"text-slate-300")},
            e("span",{className:"w-3.5 h-3.5 rounded-full border border-white/20",style:{backgroundColor:s.swatch}}),s.label);}))),
    ),

    /* ── LAYOUT ── */
    e("div",{className:"grid grid-cols-1 xl:grid-cols-[300px_minmax(0,1fr)] gap-3 sm:gap-4 p-3 sm:p-4"},

      /* ══ LEFT · MONTHLY ANALYTICS ══ */
      e(Panel,{title:lang==="so"?"Falanqaynta Billaha Shaybaarka":"Monthly Lab Analytics",icon:"calendar-days",cls:"xl:sticky xl:top-20 self-start"},
        e("div",{className:"space-y-2"},
          [["Total Samples Tested",totals.tested,"flask-conical","text-emerald-300"],
           ["Certificates Issued",totals.certs,"badge-check","text-sky-300"],
           ["Avg. Turnaround Time",totals.avgTAT,"timer","text-amber-300"],
           ["Revenue Collected (mo.)",money(totals.collected),"banknote","text-emerald-300"],
           ["Outstanding Balances",money(totals.pending),"hourglass","text-red-300"]]
          .map(function(c){return e("div",{key:c[0],className:"flex items-center justify-between rounded-xl border border-slate-700/60 bg-slate-800/60 px-3 py-2.5"},
            e("span",{className:"text-xs text-slate-400 flex items-center gap-2"},e(Icon,{name:c[2],cls:"w-3.5 h-3.5 "+c[3]}),c[0]),
            e("b",{className:"text-sm "+c[3]},c[1]));})),
        e("div",{className:"mt-3 h-44"},
          e("div",{className:"text-[10px] uppercase tracking-widest text-slate-500 mb-1"},"Daily lab throughput — "+today.toLocaleString('en',{month:'long'})+" "+today.getFullYear()),
          e(ResponsiveContainer,{width:"100%",height:"100%"},
            e(BarChart,{data:month,margin:{top:4,right:4,left:-22,bottom:-6}},
              e(CartesianGrid,{stroke:"#1e293b",strokeDasharray:"3 3"}),
              e(XAxis,{dataKey:"day",tick:{fill:"#64748b",fontSize:9},tickLine:false,axisLine:{stroke:"#334155"}}),
              e(YAxis,{tick:{fill:"#64748b",fontSize:9},tickLine:false,axisLine:false}),
              e(Tooltip,{contentStyle:{background:"#0f172a",border:"1px solid #334155",borderRadius:10,fontSize:11}}),
              e(Legend,{wrapperStyle:{fontSize:10}}),
              e(Bar,{dataKey:"samples",name:"Samples",fill:"#34d399",radius:[2,2,0,0]}),
              e(Bar,{dataKey:"certs",name:"Certificates",fill:"#38bdf8",radius:[2,2,0,0]})))),
        e("div",{className:"mt-4 h-36"},
          e("div",{className:"text-[10px] uppercase tracking-widest text-slate-500 mb-1"},"Monthly revenue · USD"),
          e(ResponsiveContainer,{width:"100%",height:"100%"},
            e(LineChart,{data:revenue,margin:{top:4,right:4,left:-24,bottom:-5}},
              e(CartesianGrid,{stroke:"#1e293b",strokeDasharray:"3 3"}),
              e(XAxis,{dataKey:"month",tick:{fill:"#64748b",fontSize:9},tickLine:false,axisLine:{stroke:"#334155"}}),
              e(YAxis,{tick:{fill:"#64748b",fontSize:8},tickLine:false,axisLine:false}),
              e(Tooltip,{contentStyle:{background:"#0f172a",border:"1px solid #334155",borderRadius:10,fontSize:10},formatter:function(v){return money(v);}}),
              e(Line,{type:"monotone",dataKey:"collected",name:"Revenue",stroke:"#34d399",strokeWidth:2.3,dot:{r:2}}))))
      ),

      /* ══ RIGHT AREA ══ */
      e("div",{className:"grid grid-cols-1 2xl:grid-cols-2 gap-4 content-start"},

        e(EngineerPanel,{lang,duty,engineers,dutyId,setDutyId,engName,setEngName,engLic,setEngLic,addEngineer}),

        /* Module 2 — daily ledger */
        e(Panel,{title:(lang==="so"?"Taariikhda Shaqada Maanta — ":"Daily Work History — Today ")+today.toLocaleDateString(),icon:"clipboard-list",cls:"2xl:col-span-2",
          right:e("span",{className:"text-[10px] text-slate-500"},"click a row → certificate")},
          e("div",{className:"overflow-x-auto"},
            e("table",{className:"w-full text-xs"},
              e("thead",null,e("tr",{className:"text-left text-slate-500 border-b border-slate-700"},
                ["Ref","Farmer","Location","Test Tier","pH","Status","Engineer","Time"].map(function(h){return e("th",{key:h,className:"py-2 pr-3 font-medium"},h);}))),
              e("tbody",null,samples.map(function(s){
                const v=phVerdict(s.ph);
                return e("tr",{key:s.id,onClick:function(){setOpenCert(s);},onKeyDown:function(ev){if(ev.key==="Enter"||ev.key===" "){ev.preventDefault();setOpenCert(s);}},role:"button",tabIndex:0,
                  className:"border-b border-slate-800 hover:bg-emerald-900/20 focus:bg-emerald-900/30 focus:outline-none cursor-pointer transition-colors"},
                  e("td",{className:"py-2 pr-3 font-mono text-emerald-300"},s.id),
                  e("td",{className:"py-2 pr-3"},s.farmer),
                  e("td",{className:"py-2 pr-3 text-slate-400"},s.location),
                  e("td",{className:"py-2 pr-3 text-slate-400"},s.tier),
                  e("td",{className:"py-2 pr-3 font-mono font-bold"},s.ph),
                  e("td",{className:"py-2 pr-3"},e("span",{className:"px-2 py-0.5 rounded-full border text-[10px] "+v.chip},v.status)),
                  e("td",{className:"py-2 pr-3 text-slate-400"},s.engineer.split(" — ")[0]),
                  e("td",{className:"py-2 text-slate-500"},s.time));
              })))),
          e("div",{className:"mt-3 rounded-xl border border-slate-700 bg-slate-800/50 p-3"},
            e("div",{className:"text-[10px] uppercase tracking-widest text-slate-500 mb-2 flex items-center gap-1.5"},e(Icon,{name:"flask-conical",cls:"w-3.5 h-3.5"}),"Register New Sample — assigned to on-duty engineer"),
            e("div",{className:"grid grid-cols-2 lg:grid-cols-5 gap-2 text-xs"},
              e("input",{id:"s-name",placeholder:"Farmer name",className:"bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-2"}),
              e("input",{id:"s-loc",placeholder:"Farm location",className:"bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-2"}),
              e("select",{id:"s-tier",className:"bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-2"},
                Object.keys(TIERS).map(function(t){return e("option",{key:t,value:t},t);})),
              e("input",{id:"s-ph",placeholder:"Measured pH",type:"number",step:"0.1",min:"3",max:"14",className:"bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-2"}),
              e("button",{onClick:registerSample,className:"rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold"},"Add Sample"))))),

        /* Module 5 — invoices + typed payment intake */
        e(Panel,{title:uiText(lang,"finance")+" · Cash Intake",icon:"receipt",
          right:e("span",{className:"rounded-full border border-emerald-700/60 bg-emerald-950/30 px-2 py-1 text-[10px] font-bold text-emerald-300"},"NO TAX · NO FEES")},
          e("div",{className:"overflow-x-auto max-h-56 overflow-y-auto pr-1"},
            e("table",{className:"w-full text-xs"},
              e("thead",null,e("tr",{className:"text-left text-slate-500 border-b border-slate-700"},
                ["Invoice","Client Name","Currency","Method","Charge","Total USD","Paid","Balance","Status"].map(function(h){return e("th",{key:h,className:"py-2 pr-3 font-medium"},h);}))),
              e("tbody",null,invoices.map(function(v){
                const chip=v.status==="PAID"?"border-emerald-700 bg-emerald-900/40 text-emerald-300":v.status==="PARTIAL"?"border-amber-700 bg-amber-900/40 text-amber-300":"border-red-800 bg-red-900/40 text-red-300";
                return e("tr",{key:v.id,className:"border-b border-slate-800"},
                  e("td",{className:"py-1.5 pr-3 font-mono text-sky-300"},v.id),
                  e("td",{className:"py-1.5 pr-3"},v.farmer),
                  e("td",{className:"py-1.5 pr-3 font-mono text-slate-400"},v.currency),
                  e("td",{className:"py-1.5 pr-3 text-slate-400"},v.gw),
                  e("td",{className:"py-1.5 pr-3"},money(v.subtotal)),
                  e("td",{className:"py-1.5 pr-3 font-bold text-emerald-300"},money(v.total)),
                  e("td",{className:"py-1.5 pr-3"},money(v.paid)),
                  e("td",{className:"py-1.5 pr-3 "+(v.balance>0?"text-red-300":"text-slate-500")},money(v.balance)),
                  e("td",{className:"py-1.5"},v.status==="PAID"
                    ? e("span",{className:"px-2 py-0.5 rounded-full border text-[10px] "+chip},"PAID")
                    : e("button",{onClick:function(){settleInvoice(v.id);},title:"Settle full balance",className:"px-2 py-0.5 rounded-full border text-[10px] "+chip+" hover:opacity-80"},v.status+" ⧉ settle")));
              }))))),
          e("div",{className:"mt-3 rounded-xl border border-slate-700 bg-slate-800/50 p-3"},
            e("div",{className:"text-[10px] uppercase tracking-widest text-slate-500 mb-2 flex items-center gap-1.5"},e(Icon,{name:"banknote",cls:"w-3.5 h-3.5"}),"Cash Intake · Client, charge, USD currency & payment method"),
            e("div",{className:"grid grid-cols-2 lg:grid-cols-7 gap-2 text-xs"},
              e("input",{value:payName,onChange:function(ev){setPayName(ev.target.value);},placeholder:"Client Name","aria-label":"Client Name",className:"bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-2"}),
              e("select",{value:payTier,onChange:function(ev){pickTier(ev.target.value);},className:"bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-2"},
                Object.keys(TIERS).map(function(t){return e("option",{key:t,value:t},t+" ~ "+money(TIERS[t]));})),
              e("input",{value:payBase,onChange:function(ev){setPayBase(ev.target.value);},type:"number",min:"0",step:"0.01","aria-label":"Charge in USD",title:"Charge in USD (tier is only a suggestion)",className:"bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-2"}),
              e("input",{value:"USD",readOnly:true,"aria-label":"Currency",className:"bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-2 font-mono text-emerald-300"}),
              e("select",{value:payGw,onChange:function(ev){setPayGw(ev.target.value);},"aria-label":"Payment method",className:"bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-2"},
                PAYMENT_METHODS.map(function(g){return e("option",{key:g,value:g},g);})),
              e("input",{value:payPaid,onChange:function(ev){setPayPaid(ev.target.value);},type:"number",min:"0",step:"0.01",placeholder:"Amount paid USD",title:"What the farmer handed over today",className:"bg-slate-900 border border-emerald-700 rounded-lg px-2.5 py-2"}),
              e("button",{onClick:receivePay,disabled:!payName.trim()||baseNum<=0,className:"rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 text-white font-semibold"},"Record")),
            e("div",{className:"mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px]"},
              e("span",{className:"text-slate-400"},"Charge ",e("b",null,money(live.subtotal))),
              e("span",{className:"rounded-full border border-emerald-700/60 bg-emerald-950/30 px-2 py-0.5 text-emerald-300"},"Tax disabled · gateway fees disabled"),
              e("span",{className:"text-slate-400"},"Total Due ",e("b",{className:"text-emerald-300"},money(live.total))," USD"),
              e("span",{className:paidNum==null?"text-slate-500":"text-amber-300"},"Paid ",e("b",null,paidNum==null?"—":money(paidNum))),
              liveCredit>0?e("span",{className:"text-sky-300"},"Change/Credit ",e("b",null,money(liveCredit)))
                :e("span",{className:"text-red-300"},"Balance Owing ",e("b",null,money(liveBalance)))))),

        /* revenue chart */
        e(Panel,{title:"Revenue Trends",icon:"trending-up"},
          e("div",{className:"h-64"},
            e(ResponsiveContainer,{width:"100%",height:"100%"},
              e(LineChart,{data:revenue,margin:{top:4,right:8,left:-14,bottom:-4}},
                e(CartesianGrid,{stroke:"#1e293b",strokeDasharray:"3 3"}),
                e(XAxis,{dataKey:"month",tick:{fill:"#64748b",fontSize:10},tickLine:false,axisLine:{stroke:"#334155"}}),
                e(YAxis,{tick:{fill:"#64748b",fontSize:10},tickLine:false,axisLine:false}),
                e(Tooltip,{contentStyle:{background:"#0f172a",border:"1px solid #334155",borderRadius:10,fontSize:11},formatter:function(v){return money(v);}}),
                e(Legend,{wrapperStyle:{fontSize:11}}),
                e(Line,{type:"monotone",dataKey:"collected",name:"Income collected",stroke:"#34d399",strokeWidth:2.4,dot:{r:2.5}}),
                e(Line,{type:"monotone",dataKey:"pending",name:"Outstanding balances",stroke:"#f59e0b",strokeWidth:2.2,strokeDasharray:"6 4",dot:{r:2.2}})))),

        e(RotationPlanner,{lang,samples:samples}),

        /* Module 5 — CROP PATHOLOGY · asynchronous dictionary */
        e(Panel,{title:uiText(lang,"pathology")+" · Disease & Treatment Intelligence",icon:"stethoscope",cls:"2xl:col-span-2",
          right:e("span",{className:"rounded-full border border-red-800/70 bg-red-950/30 px-2 py-1 text-[10px] font-bold text-red-200"},diseases?diseases.length+" classifications":"loading…")},
          /* control sector — category tabs with count badges + fuzzy search */
          e("div",{className:"flex flex-wrap items-center gap-1.5"},
            DISEASE_CATEGORIES.map(function(c){return e("button",{key:c,onClick:function(){setCatTab(c);},
              className:"flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-xs transition "+(catTab===c?"border-emerald-500 bg-emerald-900/40 text-emerald-200":"border-slate-700 text-slate-400 hover:border-slate-500")},
              e(Icon,{name:DISEASE_CAT_ICONS[c],cls:"w-3.5 h-3.5"}),c,
              e("span",{className:"ml-0.5 rounded-full bg-slate-800 border border-slate-600 px-1.5 py-0.5 text-[10px] font-bold"},String(catCounts[c]!=null?catCounts[c]:0)));}),
            e("div",{className:"relative flex-1 min-w-[220px]"},
              e(Icon,{name:"search",cls:"w-4 h-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none"}),
              e("input",{value:disSearch,onChange:function(ev){setDisSearch(ev.target.value);},placeholder:"Fuzzy search host, disease, pathogen or symptom text…",className:"w-full bg-slate-900 border border-slate-700 focus:border-emerald-500 rounded-lg pl-8 pr-3 py-2 text-xs"}))),
          /* async body — skeleton during the 600ms mock fetch */
          diseases==null ? e("div",{className:"mt-3 space-y-2"},
            e("div",{className:"flex items-center gap-2 text-xs text-slate-500"},
              e(Icon,{name:"refresh-cw",cls:"w-3.5 h-3.5 animate-spin"}),
              "Syncing disease repository… (600 ms mock API latency)"),
            [0,1,2,3].map(function(i){return e("div",{key:i,className:"animate-pulse rounded-xl bg-slate-800/70 border border-slate-700/60 h-14"});}))
          : e("div",{className:"grid grid-cols-1 lg:grid-cols-[300px_1fr] gap-3 mt-3"},
            /* Step 1 — searchable host-card grid */
            e("div",null,
              e("div",{className:"text-[10px] uppercase tracking-widest text-slate-500 mb-1.5"},"Step 1 · Target Host — "+hostGroups.length+" match"+(hostGroups.length===1?"":"es")),
              e("div",{className:"grid grid-cols-1 sm:grid-cols-2 gap-1.5 max-h-64 overflow-y-auto pr-1"},
                hostGroups.map(function(g){return e("button",{key:g.plant,onClick:function(){setSelHost(selHost===g.plant?null:g.plant);},
                  className:"rounded-xl border px-3 py-2.5 text-left transition "+(selHost===g.plant?"border-emerald-500 bg-emerald-900/25":"border-slate-700 bg-slate-800/60 hover:border-slate-500")},
                  e("div",{className:"flex items-center gap-2"},
                    e(Icon,{name:DISEASE_CAT_ICONS[g.cat]||"leaf",cls:"w-4 h-4 "+(selHost===g.plant?"text-emerald-300":"text-slate-500")}),
                    e("div",{className:"text-sm font-bold"},g.plant)),
                  e("div",{className:"text-[10px] text-slate-500 mt-0.5"},g.cat+" · "+g.items.length+" diagnosis"+(g.items.length>1?"es":"")));})),
              /* Farmer Field Issue integration */
              e("div",{className:"mt-3 rounded-xl border border-slate-700 bg-slate-800/50 p-3"},
                e("div",{className:"text-[10px] uppercase tracking-widest text-slate-500 mb-2 flex items-center gap-1.5"},
                  e(Icon,{name:"clipboard-list",cls:"w-3.5 h-3.5"}),"Writable Farmer Field Issue Logger"),
                e("input",{value:issueClient,onChange:function(ev){setIssueClient(ev.target.value);},list:"farmer-client-suggestions",
                  placeholder:"Type farmer or client name","aria-label":"Farmer or client name",
                  className:"w-full mb-1.5 bg-slate-900 border border-slate-700 focus:border-emerald-500 rounded-lg px-2.5 py-2 text-xs"}),
                e("datalist",{id:"farmer-client-suggestions"},FARMERS.map(function(f){return e("option",{key:f[0],value:f[0]},f[1]);})),
                e("select",{value:issueDisease,onChange:function(ev){setIssueDisease(ev.target.value);},className:"w-full mb-1.5 bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-2 text-xs"},
                  e("option",{value:""},"— link a filtered disease card —"),
                  diseaseFiltered.map(function(d){return e("option",{key:d.disease+"|"+d.plant,value:d.disease+"|"+d.plant},d.plant+" — "+d.disease);})),
                e("div",{className:"mb-1.5 text-[9px] text-slate-500"},diseaseFiltered.length+" diagnoses linked to the current pathology filters; clicking a diagnosis selects it here."),
                e("button",{onClick:logIssue,disabled:!issueClient.trim()||!issueDisease,
                  className:"w-full rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 text-white text-xs font-semibold px-3 py-2"},
                  "Log Field Issue & Issue Treatment Sheet")),
              issueFeed.length>0 && e("div",{className:"mt-2"},
                e("div",{className:"text-[10px] uppercase tracking-widest text-slate-500 mb-1"},"Live diagnostic history (latest "+issueFeed.length+")"),
                e("div",{className:"max-h-36 overflow-y-auto space-y-1 pr-1"},
                  issueFeed.map(function(it,i){return e("div",{key:i,className:"rounded-lg border border-slate-700 bg-slate-900 px-2 py-1.5 text-[11px] flex items-center gap-1.5 flex-wrap"},
                    e("span",{className:"text-slate-500"},"["+it.t+"]"),
                    e("b",null,it.client),
                    e("span",{className:"text-slate-600"},it.cat),
                    e("span",{className:"text-amber-300"},it.plant+" → "+it.disease),
                    e("span",{className:"text-slate-600 ml-auto"},"sheet issued ✓"));}))),
            ),
            /* Step 2 — diagnoses of the chosen host */
            e("div",null,
              selHost==null ? e("div",{className:"h-full min-h-44 flex flex-col items-center justify-center gap-2 text-slate-600 text-xs border border-dashed border-slate-700 rounded-xl"},
                e(Icon,{name:"scan-search",cls:"w-6 h-6"}),
                "Search or filter hosts, then click a card to list its diagnoses")
              : e("div",null,
                e("div",{className:"text-[10px] uppercase tracking-widest text-slate-500 mb-1.5"},"Step 2 · "+selHost+" diagnoses — click any card to open its treatment manifest"),
                e("div",{className:"space-y-1.5 max-h-[26rem] overflow-y-auto pr-1"},
                  ((hostGroups.filter(function(g){return g.plant===selHost;})[0])||{items:[]}).items.map(function(d){return e("button",{key:d.disease,onClick:function(){setIssueDisease(d.disease+"|"+d.plant);setManifest(d);},
                    className:"w-full rounded-xl border border-slate-700 bg-slate-800/60 hover:border-amber-500 px-3 py-3 text-left transition"},
                    e("div",{className:"text-sm font-bold text-amber-300 flex items-center gap-2"},
                      e(Icon,{name:"bug",cls:"w-4 h-4"}),d.disease,
                      e("span",{className:"ml-auto text-[10px] font-normal text-slate-500 border border-slate-600 rounded-full px-2 py-0.5"},d.cat)),
                    e("div",{className:"text-[11px] text-slate-500 italic mt-0.5"},d.cause),
                    e("div",{className:"mt-1.5 flex flex-wrap gap-1"},
                      d.symptoms.slice(0,3).map(function(sx){return e("span",{key:sx,className:"rounded-full border border-slate-600 bg-slate-900 px-2 py-0.5 text-[10px] text-slate-400"},sx);})));})))),
          /* Step 3 — Actionable Treatment Manifest overlay window */
          manifest && e("div",{className:"fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4",onClick:function(){setManifest(null);}},
            e("div",{className:"max-w-xl w-full rounded-2xl border border-amber-700/60 bg-slate-900 shadow-2xl p-5 max-h-[85vh] overflow-y-auto",onClick:function(ev){ev.stopPropagation();}},
              e("div",{className:"flex items-start gap-2"},
                e("div",null,
                  e("div",{className:"text-[10px] uppercase tracking-widest text-amber-400 font-bold"},"Step 3 · Actionable Treatment Manifest"),
                  e("div",{className:"text-lg font-bold mt-0.5"},manifest.disease,
                    e("span",{className:"text-slate-500 text-sm font-normal ml-2"},manifest.plant+" · "+manifest.cat))),
                e("button",{onClick:function(){setManifest(null);},className:"ml-auto p-1.5 rounded-lg border border-slate-700 hover:border-red-500 text-slate-400"},
                  e(Icon,{name:"x",cls:"w-4 h-4"}))),
              e("div",{className:"mt-3 rounded-lg bg-slate-900/70 border border-slate-700 p-3"},
                e("div",{className:"text-[10px] uppercase tracking-widest text-slate-500 mb-0.5"},"Biological root cause / pathogen"),
                e("div",{className:"text-sm italic text-red-300"},manifest.cause)),
              e("div",{className:"mt-2 rounded-lg bg-slate-900/70 border border-slate-700 p-3"},
                e("div",{className:"text-[10px] uppercase tracking-widest text-slate-500 mb-1"},"Observable visual symptoms"),
                e("div",{className:"flex flex-wrap gap-1.5"},
                  manifest.symptoms.map(function(sx){return e("span",{key:sx,className:"rounded-full border border-amber-700/60 bg-amber-950/30 px-2.5 py-1 text-[11px] text-amber-200"},sx);}))),
              e("div",{className:"mt-2 rounded-lg bg-slate-900/70 border border-slate-700 p-3"},
                e("div",{className:"text-[10px] uppercase tracking-widest text-slate-500 mb-1"},"Immediate field mitigation steps"),
                e("ul",{className:"text-sm space-y-1"},manifest.immediate.map(function(step,i){return e("li",{key:i,className:"flex gap-2"},
                  e("span",{className:"text-emerald-400 font-bold"},(i+1)+"."),
                  e("span",null,step));}))),
              e("div",{className:"mt-2 rounded-lg bg-slate-900/70 border border-slate-700 p-3"},
                e("div",{className:"text-[10px] uppercase tracking-widest text-slate-500 mb-0.5"},"Chemical / cultural treatment programme"),
                e("div",{className:"text-sm text-sky-300"},manifest.remedy)),
              e("button",{onClick:function(){appendIssue(manifest);setManifest(null);},
                className:"mt-3 w-full rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold px-3 py-2 flex items-center justify-center gap-2"},
                e(Icon,{name:"history",cls:"w-3.5 h-3.5"}),"Log issue to treatment timeline")))
            ),
        ),
      ),

    /* footer */
    e("footer",{className:"px-4 pb-4 text-[10px] text-slate-500 flex items-center gap-2"},
      e(Icon,{name:"satellite",cls:"w-3.5 h-3.5 text-sky-400"}),
      "Somali SpatialBio Engine · LabOps LIMS — fully local state, same-origin assets. Currency: USD."),

    /* certificate modal */
    openCert && e(Certificate,{sample:openCert,onClose:function(){setOpenCert(null);},
      onIssued:function(){ if(!isSampleIds.has(openCert.id)){isSampleIds.add(openCert.id);setIssued(function(i){return i+1;});} }}),
  );
}

/* self-check: offline-safe vendor guard */
(function(){
  var root=document.getElementById("root");
  if(!window.React||!window.ReactDOM||!window.Recharts||!window.lucide){
    root.innerHTML='<div style="margin:2rem;padding:1rem;border:2px solid #ef4444;border-radius:12px;color:#fff;background:#7f1d1d;font-family:sans-serif">⚠ LIMS library load failure — a vendored asset failed to load. Check <code>/web/vendor/</code> files.</div>';
    return;
  }
  ReactDOM.createRoot(root).render(e(App));
})();
