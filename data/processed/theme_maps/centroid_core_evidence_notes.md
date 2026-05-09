# Centroid Core Evidence Notes

Source snapshot: `data/processed/theme_maps/unit_embedding_theme_map.json`
Method: unit-level averaged segment embeddings + Tibetan 120-segment section windows + k=12 MiniBatchKMeans + PCA projection

每个星系取 `core_units[0]`，即该 cluster 中离 centroid 最近的代表单位。摘录为首段、正文中部、末段附近样本；藏传 section window 为 120 个连续 segment 的代理章级单位。

## 汉传 (trad-han)

### 星系 01 · 月燈三昧經 / 菩薩從兜術天降神母胎說廣普經

- Core: **月燈三昧經 · 卷2** T0639
- Unit type: `juan`; cluster units: `1026`; unit segments: `535`; centroid sim: `0.9934`
- Gloss coverage in sampled unit: `0/535`
- Samples:
  - `pos 253 / T0639-CBETA-253` 爾時，世尊告月光童子言：「過去久遠無量無...
    - text: 爾時，世尊告月光童子言：「過去久遠無量無邊不可思議過阿僧祇劫，爾時有佛號曰聲德如來、應、正遍知、明行足、善逝、世間解、無上士、調御丈夫、天人師、佛、世尊出現於世。
  - `pos 254 / T0639-CBETA-254` 「童子！爾時聲德如來、應、正遍知於初會眾...
    - text: 「童子！爾時聲德如來、應、正遍知於初會眾集有八億聲聞，皆阿羅漢，諸漏已盡，逮得己利，盡諸有結，依於正教，心善解脫，能到一切心自在岸；第二會集有七億眾、第三會集有六億眾，一切亦是大阿羅漢，諸漏已盡，逮得己利，盡諸有結，依於正教，心善解脫，能到一切心自在岸。
  - `pos 255 / T0639-CBETA-255` 「童子！爾時彼佛壽四萬歲，時閻浮提安隱豐...
    - text: 「童子！爾時彼佛壽四萬歲，時閻浮提安隱豐樂，人民熾盛，普遍充滿。
  - `pos 519 / T0639-CBETA-519` 慢為眾苦本，諸導師所說，
    - text: 慢為眾苦本，諸導師所說，
  - `pos 520 / T0639-CBETA-520` 有慢苦增長，離之則苦滅。
    - text: 有慢苦增長，離之則苦滅。
  - `pos 521 / T0639-CBETA-521` 雖修世三昧，而不離我想，
    - text: 雖修世三昧，而不離我想，
  - `pos 785 / T0639-CBETA-785` 菩薩云何能現證？願為我說是法母。
    - text: 菩薩云何能現證？願為我說是法母。
  - `pos 786 / T0639-CBETA-786` 於一切法到彼岸，言說法句已修學，
    - text: 於一切法到彼岸，言說法句已修學，
  - `pos 787 / T0639-CBETA-787` 己自無疑除他疑，為我顯示佛菩薩。」
    - text: 己自無疑除他疑，為我顯示佛菩薩。」

### 星系 04 · Numbered Discour / Connected Discou

- Core: **增一阿含经 · 卷23** T0125
- Unit type: `juan`; cluster units: `451`; unit segments: `200`; centroid sim: `0.9835`
- Gloss coverage in sampled unit: `0/200`
- Samples:
  - `pos 3691 / T0125-CBETA-3691` 聞如是：
    - text: 聞如是：
  - `pos 3692 / T0125-CBETA-3692` 一時，佛在舍衛國祇樹給孤獨園。
    - text: 一時，佛在舍衛國祇樹給孤獨園。
  - `pos 3693 / T0125-CBETA-3693` 爾時，生漏婆羅門往至世尊所，共相問訊，在...
    - text: 爾時，生漏婆羅門往至世尊所，共相問訊，在一面坐。爾時，婆羅門白世尊曰：「在閑居穴處，甚為苦哉！獨處隻步，用心甚難。」
  - `pos 3790 / T0125-CBETA-3790` 是時，諸比丘聞佛所說，歡喜奉行。
    - text: 是時，諸比丘聞佛所說，歡喜奉行。
  - `pos 3791 / T0125-CBETA-3791` 聞如是：
    - text: 聞如是：
  - `pos 3792 / T0125-CBETA-3792` 一時，佛在舍衛國祇樹給孤獨園。爾時世尊與...
    - text: 一時，佛在舍衛國祇樹給孤獨園。爾時世尊與大比丘眾五百人俱。
  - `pos 3888 / T0125-CBETA-3888` 爾時，諸比丘聞佛所說，歡喜奉行。
    - text: 爾時，諸比丘聞佛所說，歡喜奉行。
  - `pos 3889 / T0125-CBETA-3889` 增上、坐、行跡無常、園觀池
    - text: 增上、坐、行跡無常、園觀池
  - `pos 3890 / T0125-CBETA-3890` 無漏、無息、禪四樂、無諍訟
    - text: 無漏、無息、禪四樂、無諍訟

### 星系 05 · Mahaprajnaparami / Mahasamnipata Su

- Core: **大智度论 · 卷72** T1509
- Unit type: `juan`; cluster units: `397`; unit segments: `235`; centroid sim: `0.9809`
- Gloss coverage in sampled unit: `0/235`
- Samples:
  - `pos 18755 / T1509-CBETA-18755` 【經】
    - text: 【經】
  - `pos 18756 / T1509-CBETA-18756` 爾時，欲界諸天子、色界諸天子以天末栴檀香...
    - text: 爾時，欲界諸天子、色界諸天子以天末栴檀香，以天青蓮華、赤蓮花、紅蓮華、白蓮華遙散佛上，來至佛所，頂禮佛足，一面住，白佛言：「世尊！諸佛阿耨多羅三藐三菩提甚深、難見、難解、不可思惟知、微妙寂滅，智者能知，一切世間所不能信。何以故？是深般若波羅蜜中，如是說：『色即是薩婆若，薩婆若即是色；乃至一切種智即是薩婆若，薩婆若即是一切種智。色如相、薩婆若如相，是一如，無二無別；乃至一切種智如相、薩婆若如相，一如，無二無別。』」
  - `pos 18757 / T1509-CBETA-18757` 佛告欲、色界諸天子：「如是！如是！諸天子...
    - text: 佛告欲、色界諸天子：「如是！如是！諸天子！色即是薩婆若，薩婆若即是色；乃至一切種智即是薩婆若，薩婆若即是一切種智。色如相乃至一切種智如相，一如，無二無別。諸天子！以是義故，佛初成道時，心樂嘿然，不樂說法。何以故？是諸佛阿耨多羅三藐三菩提法甚深、難見、難解、不可思惟知、微妙寂滅，智者能知，一切世間所不能信。何以故？阿耨多羅三藐三菩提，無得者、無得處、無得時，是名諸法甚深相，所謂無有二法。諸天子！如虛空甚深故，是法甚深；如甚深故，是法甚深；法性甚深、實際甚深、不可思議、無邊甚深故，是法甚深；無來無去甚深故，是法甚深；不生不滅、無垢無淨、無知無得甚深故，是法甚深。諸天子！我甚深乃至知者、見者甚深故，是法甚深。諸天子！色甚深、受想行識甚深故，是法甚深。檀波羅蜜甚深乃至般若波羅蜜甚深故，是法甚深。內空乃至無法有法空甚深故...
  - `pos 18871 / T1509-CBETA-18871` 舍利弗言：「不。」
    - text: 舍利弗言：「不。」
  - `pos 18872 / T1509-CBETA-18872` 「離色，有法於阿耨多羅三藐三菩提退還不？...
    - text: 「離色，有法於阿耨多羅三藐三菩提退還不？」
  - `pos 18873 / T1509-CBETA-18873` 舍利弗言：「不。」
    - text: 舍利弗言：「不。」
  - `pos 18987 / T1509-CBETA-18987` 上來舊法、客法，本末具足，今世得善法，智...
    - text: 上來舊法、客法，本末具足，今世得善法，智慧無礙；捨身，得法身無礙，隨意至十方教化眾生，於十方佛前修集善法。
  - `pos 18988 / T1509-CBETA-18988` 「聞是法時，二千菩薩得無生法忍」者，是品...
    - text: 「聞是法時，二千菩薩得無生法忍」者，是品說如微妙深法，亦說有行，善門、智門，二行具足。但說如法，所利少；若說有法，所利亦少。今說有、無二法，具足故，得無生法忍；譬如二輪具足故，能有所至。
  - `pos 18989 / T1509-CBETA-18989` 此中善說二諦故，二千菩薩得無生法忍。
    - text: 此中善說二諦故，二千菩薩得無生法忍。

### 星系 08 · Mahasamnipata Su / 仁王護國般若波羅蜜多經

- Core: **大方等大集经 · 卷40** T0397
- Unit type: `juan`; cluster units: `386`; unit segments: `79`; centroid sim: `0.9709`
- Gloss coverage in sampled unit: `0/79`
- Samples:
  - `pos 6188 / T0397-CBETA-6188` 爾時，一切諸天大王并其眷屬、一切龍王、一...
    - text: 爾時，一切諸天大王并其眷屬、一切龍王、一切夜叉王、阿修羅王、迦樓羅王、緊陀羅王、摩睺羅伽王、薜荔多王、毘舍遮王、富單那王，乃至迦吒富單那等一切諸王，各并眷屬禮拜於佛，同心合掌，作如是言：「世尊！我等從今在在處處，若有比丘或比丘尼、諸優婆塞及優婆夷，但有信心若男若女，能作如是念不淨觀寂滅三昧，如前佛說善根因緣得攝心住者，我等一切天諸眷屬，乃至清淨信心之人，或男或女，常當救濟猶如導師，令彼身心及其眷屬為作供養，衣食、床鋪、臥具、湯藥、種種資生所須皆與，如是具足令其安隱，更不愁於一十五種濁惡之事。設復有者，我等於中常共加護。何者名為十五濁心？所謂或以石撩，或以杖打，或以刀斫，或以槊貫，或毒藥中，或崖上擲，或復惡人，或復不信，或四大動，我為作護；或以惡心送彼人所好飲食湯藥者，我為作護；貪瞋、妬嫉、兩舌、惡口，如是惡事欲...
  - `pos 6189 / T0397-CBETA-6189` 「或比丘，或比丘尼，或優婆塞，或優婆夷，...
    - text: 「或比丘，或比丘尼，或優婆塞，或優婆夷，或餘信心男子、女人，或今現在或復當來，乃至劫盡末法世時。何者名為末法世時？謂讀誦人無不依於波羅提木叉道中行。若不坐禪則不能得於三摩提，乃至不得第四之果，乃至不得寂滅三昧，是則名為末法世時。若如上說，初夜後夜不曾睡眠，讀誦是經或坐禪定，如是住者，彼諸眷屬、比丘、比丘尼、優婆塞、優婆夷，乃至信心或男或女、一切眷屬乃至住處，或復聚落都邑國城，或阿蘭若處，或聚落主家，隨所在處有此十五濁者，我盡救濟為作擁護，令是諸惡一切悉除。
  - `pos 6190 / T0397-CBETA-6190` 「於何聚落有福德人常住之處？或多人住或一...
    - text: 「於何聚落有福德人常住之處？或多人住或一人住，乃至復有一日一夜修福德者，乃至一日一夜所住處者，或復城邑或聚落家，我皆救濟為作護助，不令其人經於惡事，無問一切諸檀越家，或復剎利，或婆羅門、毘舍、首陀，或男，或女、小男、小女，一切救濟常為守護不令入惡。若有如是修福德者身心精進，若有人供養禮拜恭敬種種供給，或為造房或大寺舍，或林或苑或作衣裳，食飲所須坐臥處所，或復病患湯藥針灸種種醫療，如是檀越，我等如是十五濁中一切悉護。
  - `pos 6226 / T0397-CBETA-6226` 爾時，一切無量眾生生大歡喜，踊躍無量不可...
    - text: 爾時，一切無量眾生生大歡喜，踊躍無量不可思議未曾聞見。又其六根一切清淨現佛身中，或坐、或行、或住、或臥，復見如來一一毛孔出無量光。譬如十方恒河沙等日月光明，亦如一切恒河沙等大摩尼珠，亦如恒河沙等十地菩薩摩訶薩眾，一時普放大焰光明。如是光明悉能遍照十方佛土，如是如來一一毛孔所出光明，處處皆滿於十方剎最為殊勝。
  - `pos 6227 / T0397-CBETA-6227` 爾時，十方一切諸佛，於其剎中自在而住，各...
    - text: 爾時，十方一切諸佛，於其剎中自在而住，各為大眾異口同音稱讚我名，說於此偈：
  - `pos 6228 / T0397-CBETA-6228` 「汝觀具足功德滿，憐彼一切諸眾生，
    - text: 「汝觀具足功德滿，憐彼一切諸眾生，
  - `pos 6264 / T0397-CBETA-6264` 同共往詣娑婆國，恭敬供養釋師子。」
    - text: 同共往詣娑婆國，恭敬供養釋師子。」
  - `pos 6265 / T0397-CBETA-6265` 時諸菩薩摩訶薩等如是化作阿羅漢身說此偈已...
    - text: 時諸菩薩摩訶薩等如是化作阿羅漢身說此偈已，與於無量恒河沙等得神通力一切眾生，俱共發引來到此剎。到已頭面頂禮釋迦牟尼如來并其眷屬，恭敬圍遶三匝佛已，出所齎來種種寶物、種種寶衣、種種袈裟、種種瓔珞、種種傘蓋、種種幢幡、種種寶華、種種寶香、種種音樂偈讚歌舞，以用供養釋迦如來。供養畢已各還自剎，到自剎已坐於自座，各為於己眾稱楊讚說釋迦如來，作如是言：「釋迦如來，憐愍教化一切眾生，能與眾生一切利益。」
  - `pos 6266 / T0397-CBETA-6266` 是諸菩薩各自眾中如是稱說，彼眾聞已悉皆讚...
    - text: 是諸菩薩各自眾中如是稱說，彼眾聞已悉皆讚歎釋迦如來，既讚歎已無量無數阿僧祇眾生，發阿耨多羅三藐三菩提心。或復有於辟支佛乘而發心者，或復有於聲聞乘中而發心者，各各乘中得不退道。有得種種陀羅尼忍種種善根，亦見此土娑婆佛剎諸眾生等入釋迦如來身中。是諸眾生見此不可思議神德變已，無量阿僧祗恒河沙等眾生，皆發阿耨多羅三藐三菩提心。其中或有發聲聞辟支佛心者，各於自乘得不退轉；或有作於轉輪聖王微妙之身得受記別。

### 星系 03 · Great Prajna Par

- Core: **大般若波罗蜜多经 · 卷456** T0220
- Unit type: `juan`; cluster units: `295`; unit segments: `73`; centroid sim: `0.9763`
- Gloss coverage in sampled unit: `0/73`
- Samples:
  - `pos 42550 / T0220-CBETA-42550` 「復次，善現！若菩薩摩訶薩如是修學甚深般...
    - text: 「復次，善現！若菩薩摩訶薩如是修學甚深般若波羅蜜多方便善巧威德力故，攝持一切波羅蜜多，增長一切波羅蜜多，導引一切波羅蜜多。何以故？善現！甚深般若波羅蜜多中，含藏一切波羅蜜多故。善現！譬如薩迦耶見遍能含藏六十二見，甚深般若波羅蜜多亦復如是，含藏一切波羅蜜多。善現！譬如一切死者命根滅故諸根隨滅，甚深般若波羅蜜多亦復如是，布施等五波羅蜜多悉皆隨從，若無般若波羅蜜多，亦無一切波羅蜜多。是故，善現！若菩薩摩訶薩欲至一切波羅蜜多究竟彼岸，應學如是甚深般若波羅蜜多。
  - `pos 42551 / T0220-CBETA-42551` 「復次，善現！若菩薩摩訶薩能學如是甚深般...
    - text: 「復次，善現！若菩薩摩訶薩能學如是甚深般若波羅蜜多，於諸有情最尊最勝。何以故？是菩薩摩訶薩已能修學最上處故。
  - `pos 42552 / T0220-CBETA-42552` 「復次，善現！於意云何？於此三千大千世界...
    - text: 「復次，善現！於意云何？於此三千大千世界諸有情類寧為多不？」
  - `pos 42585 / T0220-CBETA-42585` 「世尊！若法畢竟遠離，是法不應修，亦不應...
    - text: 「世尊！若法畢竟遠離，是法不應修，亦不應遣，亦復不應有所引發，甚深般若波羅蜜多亦畢竟遠離故，於法不應有所引發。
  - `pos 42586 / T0220-CBETA-42586` 「世尊！甚深般若波羅蜜多既畢竟遠離，云何...
    - text: 「世尊！甚深般若波羅蜜多既畢竟遠離，云何可說諸菩薩摩訶薩依甚深般若波羅蜜多證得無上正等菩提？諸佛無上正等菩提亦畢竟遠離，云何遠離法能證遠離法？是故般若波羅蜜多應不可說證得無上正等菩提。」
  - `pos 42587 / T0220-CBETA-42587` 佛告善現：「善哉！善哉！如是！如是！如汝...
    - text: 佛告善現：「善哉！善哉！如是！如是！如汝所說。所以者何？善現！甚深般若波羅蜜多乃至布施波羅蜜多畢竟遠離，如是乃至一切菩薩摩訶薩行畢竟遠離，諸佛無上正等菩提畢竟遠離，一切智智亦畢竟遠離。善現！以甚深般若波羅蜜多乃至布施波羅蜜多畢竟遠離，可說菩薩摩訶薩證得畢竟遠離無上正等菩提。如是乃至以一切智智畢竟遠離，可說菩薩摩訶薩證得畢竟遠離無上正等菩提。善現！若甚深般若波羅蜜多乃至布施波羅蜜多非畢竟遠離，應非般若波羅蜜多乃至布施波羅蜜多，如是乃至若一切智智非畢竟遠離，應非一切智智。善現，以甚深般若波羅蜜多乃至布施波羅蜜多畢竟遠離，得名般若波羅蜜多乃至布施波羅蜜多，如是乃至以一切智智畢竟遠離，得名一切智智。是故，善現！諸菩薩摩訶薩非不依止甚深般若波羅蜜多，證得無上正等菩提。善現！雖非遠離法能證遠離法，而證無上正等菩提，非不依止...
  - `pos 42620 / T0220-CBETA-42620` 「諸天當知！是菩薩摩訶薩亦無所有。所以者...
    - text: 「諸天當知！是菩薩摩訶薩亦無所有。所以者何？有情離、空、非堅實、無所有故，當知菩薩亦離、空、非堅實、無所有。
  - `pos 42621 / T0220-CBETA-42621` 「諸天當知！若菩薩摩訶薩聞如是事，其心不...
    - text: 「諸天當知！若菩薩摩訶薩聞如是事，其心不驚、不恐、不怖、不憂、不悔、不沈、不沒，當知是菩薩摩訶薩行深般若波羅蜜多。
  - `pos 42622 / T0220-CBETA-42622` 「所以者何？諸色離即有情離，受、想、行、...
    - text: 「所以者何？諸色離即有情離，受、想、行、識離即有情離，眼處乃至意處離即有情離，色處乃至法處離即有情離，眼界乃至意界離即有情離，色界乃至法界離即有情離，眼識界乃至意識界離即有情離，眼觸乃至意觸離即有情離，眼觸為緣所生諸受乃至意觸為緣所生諸受離即有情離，地界乃至識界離即有情離，因緣乃至增上緣離即有情離，無明乃至老死離即有情離，布施波羅蜜多乃至般若波羅蜜多離即有情離，內空乃至無性自性空離即有情離，真如乃至不思議界離即有情離，苦、集、滅、道聖諦離即有情離，四念住乃至八聖道支離即有情離，四靜慮、四無量、四無色定離即有情離，八解脫乃至十遍處離即有情離，空、無相、無願解脫門離即有情離，淨觀地乃至如來地離即有情離，極喜地乃至法雲地離即有情離，一切陀羅尼門、三摩地門離即有情離，五眼、六神通離即有情離，如來十力乃至十八佛不共法離即...

### 星系 10 · 大乘寶雲經 / 寶雲經

- Core: **大方等大集经 · 卷25** T0397
- Unit type: `juan`; cluster units: `229`; unit segments: `83`; centroid sim: `0.9792`
- Gloss coverage in sampled unit: `0/83`
- Samples:
  - `pos 4873 / T0397-CBETA-4873` 爾時，世尊故在欲色二界中間大寶坊中，坐師...
    - text: 爾時，世尊故在欲色二界中間大寶坊中，坐師子座。放大光明猶如日月，得大自在猶如梵釋，功德高顯猶如須彌山，法界甚深猶如大海。於大眾中演說正法，初中後善字義真正，具足清淨班宣梵行，為諸菩薩淨於法印，令諸菩薩聞已修集。
  - `pos 4874 / T0397-CBETA-4874` 爾時，東方過九萬二千諸佛世界，彼有世界名...
    - text: 爾時，東方過九萬二千諸佛世界，彼有世界名曰善華，其土有佛，號曰淨住如來、應、正遍知、明行足、善逝、世間解、無上士、調御丈夫、天人師、佛、世尊，為化眾生宣說正法。
  - `pos 4875 / T0397-CBETA-4875` 有一菩薩名曰寶髻，與諸菩薩其數八千，沒彼...
    - text: 有一菩薩名曰寶髻，與諸菩薩其數八千，沒彼世界欲來此土，齎妙寶蓋欲奉如來，其蓋周覆一千世界，及諸香華欲供養佛。妙音說偈讚歎如來：
  - `pos 4913 / T0397-CBETA-4913` 「復有八種：一者、不為利養顯異惑眾；二者...
    - text: 「復有八種：一者、不為利養顯異惑眾；二者、不說自事，離一切故；三者、不讚供養，心知足故；四者、行聖種性，樂善法故；五者、隨頭陀法，不惜身命故；六者、樂於寂靜，離說世事故；七者、深心樂法，厭三界故；八者、至心護法，不惜身命故。
  - `pos 4914 / T0397-CBETA-4914` 「復有九種：一者、離九惡心，過九眾生所居...
    - text: 「復有九種：一者、離九惡心，過九眾生所居處故；二者、念淨；三者、念修；四者、增長善法；五者、心樂寂靜；六者、離煩惱熱；七者、莊嚴舍摩他；八者、勤行精進；九者、不欺眾生。
  - `pos 4915 / T0397-CBETA-4915` 「復有十種：一者、淨身三業；二者、淨口四...
    - text: 「復有十種：一者、淨身三業；二者、淨口四業；三者、淨意三業；四者、遠離嫉妬；五者、離諂曲心；六者、至心念戒；七者、為持戒故，勤行精進；八者、軟語，為調眾生；九者、受身為眾生使；十者、於諸福田不生輕慢。
  - `pos 4953 / T0397-CBETA-4953` 「菩薩修四如意足已，得四自在：一者、壽命...
    - text: 「菩薩修四如意足已，得四自在：一者、壽命自在，以自在故，雖生短命自得長壽，為調眾生，與長壽者演說正法，於長壽中能現短壽，隨是菩薩所生之處，若天若人得命自在。二者、身得自在，以自在故，隨心作身隨心作色，示現威儀為眾生故。菩薩若欲與諸眾生其身同等，高大微小悉皆能作。三者、得法自在，以自在故，能知一切世出世法，示諸眾生一切世事，於出世行心亦不退，明知甚深十二因緣，得無礙智，能為眾生說種種法。無量眾生聞是法已，發阿耨多羅三藐三菩提心。四者、願得自在，以自在故，令四大海合作一海，不來不去無有動轉如本不異，亦令三千大千世界諸須彌山合為一山，不來不去無有動轉如本不異，於四天王、三十三天無所妨礙。欲令三千大千世界悉作金寶、七寶、栴檀、華香、瓔珞，虛空水火，皆隨意成，是名菩薩得四自在。
  - `pos 4954 / T0397-CBETA-4954` 「善男子！菩薩若得四如意足，則得面見十方...
    - text: 「善男子！菩薩若得四如意足，則得面見十方諸佛，與共語言進止一處；一切梵天、帝釋、四王、阿修羅、乾闥婆、迦樓羅、緊那羅、摩睺羅伽，亦復如是。
  - `pos 4955 / T0397-CBETA-4955` 「云何莊嚴四如意足？善男子！若能供養父母...
    - text: 「云何莊嚴四如意足？善男子！若能供養父母和上師長有德，見諸眾生先意問訊，柔軟與語如語而作，視諸眾生其心平等，善心正心恭敬心慚愧心。遠離貪欲瞋恚愚癡，無欺無貪無姤無慳，營他事業如己所作，無勢力者助其力勢，泥塗之處發治土石，河㵎溝渠造作橋梁，或以身負或施船濟，常施眾生所須之物，口不說他衰惱之事，亦不譏刺他所犯罪。有犯罪者能如法除，遮諸煩惱令不生起，所重之物能以施人，既施之後心不生悔，為諸眾生發願迴向。信心以善勸諸眾生，不惜身命少欲知足，於他利養心無悕望，常念出家亦勸眾生，念善知識無心捨離。於怨親中平等無二，以種種乘施行路者，羸乏之人施床臥具，有恐怖者能為救護，視諸眾生如父母想，不輕毀戒施貧財物。有病瘦者給其醫藥，施恩於他不自稱說。終不斷絕三寶種性，常念無為。遠離世事一切諸惡不善之法，不為世法之所污染，不失菩提至心之...

### 星系 11 · 賢愚經 / 菩薩本行經

- Core: **賢愚經 · 卷1** T0202
- Unit type: `juan`; cluster units: `216`; unit segments: `135`; centroid sim: `0.9804`
- Gloss coverage in sampled unit: `0/135`
- Samples:
  - `pos 1 / T0202-CBETA-001` 如是我聞：
    - text: 如是我聞：
  - `pos 2 / T0202-CBETA-002` 一時佛在摩竭國善勝道場。初始得佛，念諸眾...
    - text: 一時佛在摩竭國善勝道場。初始得佛，念諸眾生迷網邪倒，難可教化。「若我住世，於事無益，不如遷逝無餘涅槃。」爾時梵天知佛所念，即從天下前詣佛所，頭面禮足，長跪合掌勸請：「世尊！轉于法輪，莫般涅槃！」佛答梵天：「眾生之類，塵垢所弊，樂著世樂，無有慧心。若我住世，唐勞其功，如吾所念，唯滅為快。」
  - `pos 3 / T0202-CBETA-003` 爾時梵天復更傾倒而白佛言：「世尊！今日法...
    - text: 爾時梵天復更傾倒而白佛言：「世尊！今日法海已滿，法幢已立，潤濟開導，今正是時。又諸眾生應可度者亦甚眾多，云何世尊欲入涅槃，使此萌類永失覆護？世尊往昔無數劫時，恒為眾生採集法藥，乃至一偈，以身妻子而用募求。云何不念便欲孤棄？
  - `pos 67 / T0202-CBETA-067` 阿難白佛：「不審世尊過去世中濟活三人，其...
    - text: 阿難白佛：「不審世尊過去世中濟活三人，其事云何？」
  - `pos 68 / T0202-CBETA-068` 佛告阿難：「乃往久遠阿僧祇劫，此閻浮提有...
    - text: 佛告阿難：「乃往久遠阿僧祇劫，此閻浮提有大國王，名曰摩訶羅檀囊（秦言大寶），典領小國，凡有五千。王有三子，其第一者，名摩訶富那寧，次名摩訶提婆（秦言大天），次名摩訶薩埵——此小子者，少小行慈，矜愍一切，猶如赤子。
  - `pos 69 / T0202-CBETA-069` 「爾時大王與諸群臣、夫人、太子出外遊觀，...
    - text: 「爾時大王與諸群臣、夫人、太子出外遊觀，時王疲懈，小住休息。其王三子共遊林間，見有一虎適乳二子，飢餓逼切，欲還食之。其王小子語二兄曰：『今此虎者酸苦極理，羸瘦垂死，加復初乳，我觀其志欲自噉子。』二兄答言：『如汝所云。』弟復問兄：『此虎今者，當復何食？』二兄報曰：『若得新殺熱血肉者，乃可其意。』又復問曰：『今頗有人能辦斯事，救此生命，令得存不？』二兄答言：『是為難事。』
  - `pos 133 / T0202-CBETA-133` 「時彼國王見其太子所作奇特，倍加恭敬，歡...
    - text: 「時彼國王見其太子所作奇特，倍加恭敬，歡喜無量，將其父母及其太子入宮供養，極為恭敬，哀此太子。時彼國王躬將軍馬，共善住王及須闍提太子還至本國，誅滅羅睺，立作本王，父子相繼，其國豐樂，遂致太平。」
  - `pos 134 / T0202-CBETA-134` 佛語阿難：「爾時善住王者，今現我父白淨王...
    - text: 佛語阿難：「爾時善住王者，今現我父白淨王是；爾時母者，今現我母摩訶摩耶是；爾時須闍提太子者，今我身是。」佛語阿難：「由過去世慈心孝順，供養父母，以持身肉濟父母厄，緣是功德，天上人中常生豪尊，受福無量，緣是功德，自致作佛。」
  - `pos 135 / T0202-CBETA-135` 爾時眾會，聞佛自說宿世本緣，爾時會者皆各...
    - text: 爾時眾會，聞佛自說宿世本緣，爾時會者皆各悲歎，感佛奇特慈孝之行，其中有得須陀洹者、斯陀含者、阿那含者、阿羅漢者，有發無上正真道者，有住不退地者，一切眾會皆大歡喜，頂戴奉行。

### 星系 07 · Mahaparinirvana  / 佛說大般泥洹經

- Core: **大般涅槃经 · 卷3** T0375
- Unit type: `juan`; cluster units: `115`; unit segments: `127`; centroid sim: `0.9804`
- Gloss coverage in sampled unit: `0/127`
- Samples:
  - `pos 251 / T0375-CBETA-251` 佛復告諸比丘：「汝於戒律有所疑者，今恣汝...
    - text: 佛復告諸比丘：「汝於戒律有所疑者，今恣汝問。我當解說，令汝心喜。我已修學一切諸法本性空寂，明了通達。汝等比丘莫謂如來唯修諸法本性空寂。」復告比丘：「若於戒律有所疑者，今悉可問。」
  - `pos 252 / T0375-CBETA-252` 時諸比丘白佛言：「世尊！我等無有智慧能問...
    - text: 時諸比丘白佛言：「世尊！我等無有智慧能問如來、應供、正遍知。所以者何？如來境界不可思議、所有諸定不可思議、所演教誨不可思議，是故，我等無有智慧能問如來。
  - `pos 253 / T0375-CBETA-253` 「世尊！譬如老人年百二十，身嬰長病，寢臥...
    - text: 「世尊！譬如老人年百二十，身嬰長病，寢臥床席，不能起居，氣力虛劣，餘命無幾。有一富人緣事欲行，當至他方。以百斤金寄彼老人而作是言：『我今他行，以是寶物持用相寄。或經十年、或二十年，事畢當還，還時歸我。』是老病人即便受之，而此老人復無繼嗣，其後不久病篤命終，所寄之物悉皆散失。財主行還，求索無所。如是癡人不知籌量所寄可否，是故行還求索無所，以是因緣喪失財寶。世尊！我等聲聞亦復如是，雖聞如來慇懃教戒，不能受持令得久住，如彼老人受他寄付。我今無智，於諸戒律當何所問？」
  - `pos 313 / T0375-CBETA-313` 迦葉菩薩復白佛言：「世尊！昔十五日僧布薩...
    - text: 迦葉菩薩復白佛言：「世尊！昔十五日僧布薩時，曾於具戒清淨眾中有一童子不善修習身、口、意業，在隱屏處盜聽說戒。密迹力士承佛神力，以金剛杵碎之如塵。世尊！是金剛神極成暴惡，乃能斷是童子命根。云何如來視諸眾生同於子想如羅睺羅？」
  - `pos 314 / T0375-CBETA-314` 佛告迦葉：「汝今不應作如是言。是童子者，...
    - text: 佛告迦葉：「汝今不應作如是言。是童子者，即是化人，非真實也。為欲驅遣破戒、毀法，令出眾故，金剛密迹示是化耳。迦葉！毀謗正法及一闡提——或有殺生、乃至邪見、及故犯禁——我於是等悉生悲心，同於子想如羅睺羅。
  - `pos 315 / T0375-CBETA-315` 「善男子！譬如國王，諸群臣等有犯王法，隨...
    - text: 「善男子！譬如國王，諸群臣等有犯王法，隨罪誅戮而不捨置。如來世尊不如是也，於毀法者與驅遣羯磨、呵責羯磨、置羯磨、舉罪羯磨、不可見羯磨、滅羯磨、未捨惡見羯磨。善男子！如來所以與謗法者作如是等降伏羯磨，為欲示諸行惡之人有果報故。善男子！汝今當知，如來即是施惡眾生無恐畏者。若放一光、若二、若五，或有遇者，悉令遠離一切諸惡。如來今者具有如是無量勢力。
  - `pos 375 / T0375-CBETA-375` 「善男子！譬如甜酥，八味具足；大般涅槃亦...
    - text: 「善男子！譬如甜酥，八味具足；大般涅槃亦復如是，八味具足。云何為八？一者、常，二者、恒，三者、安，四者、清涼，五者、不老，六者、不死，七者、無垢，八者、快樂，是為八味。具足八味，是故名為大般涅槃。若諸菩薩摩訶薩等安住是中，復能處處示現涅槃，是故名為大般涅槃。
  - `pos 376 / T0375-CBETA-376` 「迦葉！善男子、善女人若欲於此大般涅槃而...
    - text: 「迦葉！善男子、善女人若欲於此大般涅槃而涅槃者，皆作是學，如來常住，法、僧亦然。」
  - `pos 377 / T0375-CBETA-377` 迦葉菩薩復白佛言：「甚奇，世尊！如來功德...
    - text: 迦葉菩薩復白佛言：「甚奇，世尊！如來功德不可思議；法、僧亦爾，不可思議；是大涅槃亦不可思議。若有修學是經典者，得正法門，能為良醫；若未學者，當知是人盲無慧眼，無明所覆。」

### 星系 06 · Great Prajna Par

- Core: **大般若波罗蜜多经 · 卷420** T0220
- Unit type: `juan`; cluster units: `113`; unit segments: `83`; centroid sim: `0.9686`
- Gloss coverage in sampled unit: `0/83`
- Samples:
  - `pos 39957 / T0220-CBETA-39957` 「復次，善現！過去布施波羅蜜多過去布施波...
    - text: 「復次，善現！過去布施波羅蜜多過去布施波羅蜜多空，未來現在布施波羅蜜多未來現在布施波羅蜜多空；過去淨戒、安忍、精進、靜慮、般若波羅蜜多過去淨戒、安忍、精進、靜慮、般若波羅蜜多空，未來現在淨戒、安忍、精進、靜慮、般若波羅蜜多未來現在淨戒、安忍、精進、靜慮、般若波羅蜜多空。
  - `pos 39958 / T0220-CBETA-39958` 「善現！空中過去布施波羅蜜多不可得。何以...
    - text: 「善現！空中過去布施波羅蜜多不可得。何以故？過去布施波羅蜜多即是空，空性亦空，空中空尚不可得，何況空中有過去布施波羅蜜多可得！善現！空中未來現在布施波羅蜜多不可得。何以故？未來現在布施波羅蜜多即是空，空性亦空，空中空尚不可得，何況空中有未來現在布施波羅蜜多可得！善現！空中過去淨戒、安忍、精進、靜慮、般若波羅蜜多不可得。何以故？過去淨戒、安忍、精進、靜慮、般若波羅蜜多即是空，空性亦空，空中空尚不可得，何況空中有過去淨戒、安忍、精進、靜慮、般若波羅蜜多可得！善現！空中未來現在淨戒、安忍、精進、靜慮、般若波羅蜜多不可得。何以故？未來現在淨戒、安忍、精進、靜慮、般若波羅蜜多即是空，空性亦空，空中空尚不可得，何況空中有未來現在淨戒、安忍、精進、靜慮、般若波羅蜜多可得！
  - `pos 39959 / T0220-CBETA-39959` 「復次，善現！過去四念住過去四念住空，未...
    - text: 「復次，善現！過去四念住過去四念住空，未來現在四念住未來現在四念住空；過去四正斷、四神足、五根、五力、七等覺支、八聖道支過去四正斷乃至八聖道支空，未來現在四正斷乃至八聖道支未來現在四正斷乃至八聖道支空。
  - `pos 39997 / T0220-CBETA-39997` 「世尊！眼觸無邊際故，當知菩薩摩訶薩亦無...
    - text: 「世尊！眼觸無邊際故，當知菩薩摩訶薩亦無邊際；耳、鼻、舌、身、意觸無邊際故，當知菩薩摩訶薩亦無邊際。
  - `pos 39998 / T0220-CBETA-39998` 「世尊！眼觸為緣所生諸受無邊際故，當知菩...
    - text: 「世尊！眼觸為緣所生諸受無邊際故，當知菩薩摩訶薩亦無邊際；耳、鼻、舌、身、意觸為緣所生諸受無邊際故，當知菩薩摩訶薩亦無邊際。
  - `pos 39999 / T0220-CBETA-39999` 「世尊！布施波羅蜜多無邊際故，當知菩薩摩...
    - text: 「世尊！布施波羅蜜多無邊際故，當知菩薩摩訶薩亦無邊際；淨戒、安忍、精進、靜慮、般若波羅蜜多無邊際故，當知菩薩摩訶薩亦無邊際。
  - `pos 40037 / T0220-CBETA-40037` 「世尊！我豈能以畢竟不生般若波羅蜜多，教...
    - text: 「世尊！我豈能以畢竟不生般若波羅蜜多，教誡教授畢竟不生諸菩薩摩訶薩？
  - `pos 40038 / T0220-CBETA-40038` 「世尊！離畢竟不生，亦無菩薩摩訶薩能行無...
    - text: 「世尊！離畢竟不生，亦無菩薩摩訶薩能行無上正等菩提。
  - `pos 40039 / T0220-CBETA-40039` 「世尊！若菩薩摩訶薩聞如是說，心不沈沒亦...
    - text: 「世尊！若菩薩摩訶薩聞如是說，心不沈沒亦不憂悔，其心不驚不恐不怖，當知是菩薩摩訶薩能行般若波羅蜜多。」

### 星系 12 · Great Prajna Par

- Core: **大般若波罗蜜多经 · 卷217** T0220
- Unit type: `juan`; cluster units: `103`; unit segments: `60`; centroid sim: `0.9865`
- Gloss coverage in sampled unit: `0/60`
- Samples:
  - `pos 20861 / T0220-CBETA-20861` 「善現！無性自性空清淨故布施波羅蜜多清淨...
    - text: 「善現！無性自性空清淨故布施波羅蜜多清淨，布施波羅蜜多清淨故一切智智清淨。何以故？若無性自性空清淨，若布施波羅蜜多清淨，若一切智智清淨，無二、無二分、無別、無斷故。無性自性空清淨故淨戒、安忍、精進、靜慮、般若波羅蜜多清淨，淨戒乃至般若波羅蜜多清淨故一切智智清淨。何以故？若無性自性空清淨，若淨戒乃至般若波羅蜜多清淨，若一切智智清淨，無二、無二分、無別、無斷故。
  - `pos 20862 / T0220-CBETA-20862` 「善現！無性自性空清淨故內空清淨，內空清...
    - text: 「善現！無性自性空清淨故內空清淨，內空清淨故一切智智清淨。何以故？若無性自性空清淨，若內空清淨，若一切智智清淨，無二、無二分、無別、無斷故。無性自性空清淨故外空、內外空、空空、大空、勝義空、有為空、無為空、畢竟空、無際空、散空、無變異空、本性空、自相空、共相空、一切法空、不可得空、無性空、自性空清淨，外空乃至自性空清淨故一切智智清淨。何以故？若無性自性空清淨，若外空乃至自性空清淨，若一切智智清淨，無二、無二分、無別、無斷故。
  - `pos 20863 / T0220-CBETA-20863` 「善現！無性自性空清淨故真如清淨，真如清...
    - text: 「善現！無性自性空清淨故真如清淨，真如清淨故一切智智清淨。何以故？若無性自性空清淨，若真如清淨，若一切智智清淨，無二、無二分、無別、無斷故。無性自性空清淨故法界、法性、不虛妄性、不變異性、平等性、離生性、法定、法住、實際、虛空界、不思議界清淨，法界乃至不思議界清淨故一切智智清淨。何以故？若無性自性空清淨，若法界乃至不思議界清淨，若一切智智清淨，無二、無二分、無別、無斷故。
  - `pos 20890 / T0220-CBETA-20890` 「善現！真如清淨故布施波羅蜜多清淨，布施...
    - text: 「善現！真如清淨故布施波羅蜜多清淨，布施波羅蜜多清淨故一切智智清淨。何以故？若真如清淨，若布施波羅蜜多清淨，若一切智智清淨，無二、無二分、無別、無斷故。真如清淨故淨戒、安忍、精進、靜慮、般若波羅蜜多清淨，淨戒乃至般若波羅蜜多清淨故一切智智清淨。何以故？若真如清淨，若淨戒乃至般若波羅蜜多清淨，若一切智智清淨，無二、無二分、無別、無斷故。
  - `pos 20891 / T0220-CBETA-20891` 「善現！真如清淨故內空清淨，內空清淨故一...
    - text: 「善現！真如清淨故內空清淨，內空清淨故一切智智清淨。何以故？若真如清淨，若內空清淨，若一切智智清淨，無二、無二分、無別、無斷故。真如清淨故外空、內外空、空空、大空、勝義空、有為空、無為空、畢竟空、無際空、散空、無變異空、本性空、自相空、共相空、一切法空、不可得空、無性空、自性空、無性自性空清淨，外空乃至無性自性空清淨故一切智智清淨。何以故？若真如清淨，若外空乃至無性自性空清淨，若一切智智清淨，無二、無二分、無別、無斷故。
  - `pos 20892 / T0220-CBETA-20892` 「善現！真如清淨故法界清淨，法界清淨故一...
    - text: 「善現！真如清淨故法界清淨，法界清淨故一切智智清淨。何以故？若真如清淨，若法界清淨，若一切智智清淨，無二、無二分、無別、無斷故。真如清淨故法性、不虛妄性、不變異性、平等性、離生性、法定、法住、實際、虛空界、不思議界清淨，法性乃至不思議界清淨故一切智智清淨。何以故？若真如清淨，若法性乃至不思議界清淨，若一切智智清淨，無二、無二分、無別、無斷故。
  - `pos 20918 / T0220-CBETA-20918` 「善現！法界清淨故無明清淨，無明清淨故一...
    - text: 「善現！法界清淨故無明清淨，無明清淨故一切智智清淨。何以故？若法界清淨，若無明清淨，若一切智智清淨，無二、無二分、無別、無斷故。法界清淨故行、識、名色、六處、觸、受、愛、取、有、生、老死愁歎苦憂惱清淨，行乃至老死愁歎苦憂惱清淨故一切智智清淨。何以故？若法界清淨，若行乃至老死愁歎苦憂惱清淨，若一切智智清淨，無二、無二分、無別、無斷故。
  - `pos 20919 / T0220-CBETA-20919` 「善現！法界清淨故布施波羅蜜多清淨，布施...
    - text: 「善現！法界清淨故布施波羅蜜多清淨，布施波羅蜜多清淨故一切智智清淨。何以故？若法界清淨，若布施波羅蜜多清淨，若一切智智清淨，無二、無二分、無別、無斷故。法界清淨故淨戒、安忍、精進、靜慮、般若波羅蜜多清淨，淨戒乃至般若波羅蜜多清淨故一切智智清淨。何以故？若法界清淨，若淨戒乃至般若波羅蜜多清淨，若一切智智清淨，無二、無二分、無別、無斷故。
  - `pos 20920 / T0220-CBETA-20920` 「善現！法界清淨故內空清淨，內空清淨故一...
    - text: 「善現！法界清淨故內空清淨，內空清淨故一切智智清淨。何以故？若法界清淨，若內空清淨，若一切智智清淨，無二、無二分、無別、無斷故。法界清淨故外空、內外空、空空、大空、勝義空、有為空、無為空、畢竟空、無際空、散空、無變異空、本性空、自相空、共相空、一切法空、不可得空、無性空、自性空、無性自性空清淨，外空乃至無性自性空清淨故一切智智清淨。何以故？若法界清淨，若外空乃至無性自性空清淨，若一切智智清淨，無二、無二分、無別、無斷故。

### 星系 02 · Great Prajna Par / 佛說佛母出生三法藏般若波羅蜜多經

- Core: **大般若波罗蜜多经 · 卷502** T0220
- Unit type: `juan`; cluster units: `53`; unit segments: `67`; centroid sim: `0.9776`
- Gloss coverage in sampled unit: `0/67`
- Samples:
  - `pos 46209 / T0220-CBETA-46209` 爾時，天帝釋白佛言：「世尊！若善男子、善...
    - text: 爾時，天帝釋白佛言：「世尊！若善男子、善女人等不離一切智智心，以無所得為方便，於此般若波羅蜜多甚深經典，至心聽聞、受持、讀誦、精勤修學、如理思惟，廣為有情宣說流布，或有書寫眾寶嚴飾，復持種種上妙華鬘、塗散等香、衣服、瓔珞、寶幢、幡蓋、眾妙、珍奇、伎樂、燈明，經須臾頃供養恭敬、尊重讚歎，是善男子、善女人等由此因緣得幾許福？」
  - `pos 46210 / T0220-CBETA-46210` 佛告憍尸迦：「我還問汝，當隨意答。有善男...
    - text: 佛告憍尸迦：「我還問汝，當隨意答。有善男子、善女人等，於諸如來般涅槃後，為供養佛設利羅故，以妙七寶起窣堵波，種種珍奇間雜嚴飾，其量高大一踰繕那，廣減高半，復持種種天妙花鬘、塗散等香、衣服、瓔珞、寶幢、幡蓋、眾妙、珍奇、伎樂、燈明，盡其形壽供養恭敬、尊重讚歎。於意云何？是善男子、善女人等由此因緣得福多不？」
  - `pos 46211 / T0220-CBETA-46211` 天帝釋言：「甚多！世尊！甚多！善逝！」
    - text: 天帝釋言：「甚多！世尊！甚多！善逝！」
  - `pos 46241 / T0220-CBETA-46241` 時，天帝釋見已念言：「將非惡魔化作斯事欲...
    - text: 時，天帝釋見已念言：「將非惡魔化作斯事欲來惱佛，并與般若波羅蜜多而作留難？何以故？如是四軍嚴飾殊麗，摩揭陀國影堅大王四種勝軍所不能及，憍薩羅國勝軍大王四種勝軍亦不能及，劫比羅國釋種大王四種勝軍亦不能及，吠舍離國栗呫毘王四種勝軍亦不能及，吉祥茅國諸力士王四種勝軍亦不能及，由斯觀察，如是四軍定是惡魔之所化作。惡魔長夜伺求佛短，壞諸有情所修勝事，我當誦念從佛所受甚深般若波羅蜜多，令彼惡魔復道而去。」
  - `pos 46242 / T0220-CBETA-46242` 時，天帝釋念已，便誦甚深般若波羅蜜多，於...
    - text: 時，天帝釋念已，便誦甚深般若波羅蜜多，於是惡魔復道而去，甚深般若波羅蜜多大神呪王力所逼故。
  - `pos 46243 / T0220-CBETA-46243` 爾時，會中所有四大王眾天乃至色究竟天，俱...
    - text: 爾時，會中所有四大王眾天乃至色究竟天，俱時化作諸妙天花及香鬘等種種供具，踊身空中而散佛上，合掌恭敬同白佛言：「願此般若波羅蜜多在贍部洲人中久住。所以者何？乃至般若波羅蜜多在贍部洲人間流布，當知是處佛、法、僧寶常不滅沒，於此三千大千世界乃至十方無量無數無邊佛國亦復如是，由是因緣，諸菩薩摩訶薩所修勝行亦可了知。隨諸方域有善男子、善女人等，以淨信心書持般若波羅蜜多供養恭敬，當知是處有妙光明除滅闇冥生諸勝福。」
  - `pos 46273 / T0220-CBETA-46273` 「憍尸迦！若善男子、善女人等欲得如是現在...
    - text: 「憍尸迦！若善男子、善女人等欲得如是現在未來無斷無盡功德勝利，應於般若波羅蜜多甚深經典，以應一切智智心，用無所得為方便，至心聽聞、受持、讀誦、精勤修學、如理思惟、書寫、解說、廣令流布，復持種種上妙花鬘乃至燈明供養恭敬、尊重讚歎。
  - `pos 46274 / T0220-CBETA-46274` 「復次，憍尸迦！若善男子、善女人等書寫如...
    - text: 「復次，憍尸迦！若善男子、善女人等書寫如是甚深般若波羅蜜多，種種莊嚴置清淨處供養恭敬、尊重讚歎。時，此三千大千國土及餘十方無邊世界，所有四大王眾天乃至廣果天已發無上菩提心者常來是處，觀禮、讀誦如是般若波羅蜜多，供養恭敬、尊重讚歎，右遶禮拜合掌而去；所有淨居天亦常來此，觀禮、讀誦、供養恭敬、尊重讚歎，右遶禮拜合掌而去；有大威德諸龍、藥叉廣說乃至人非人等亦常來此，觀禮、讀誦、供養恭敬、尊重讚歎，右遶禮拜合掌而去。憍尸迦！是善男子、善女人等應作是念：『今此三千大千國土及餘十方無邊世界，一切天、龍廣說乃至人非人等常來至此，觀禮、讀誦我所書寫甚深般若波羅蜜多，供養恭敬、尊重讚歎，右遶禮拜合掌而去，此我則為已設法施。』作是念已歡喜踊躍，令所獲福倍復增長。
  - `pos 46275 / T0220-CBETA-46275` 「憍尸迦！是善男子、善女人等，由此三千大...
    - text: 「憍尸迦！是善男子、善女人等，由此三千大千國土及餘十方無邊世界天、龍、藥叉、阿素洛等常隨擁護，不為一切人非人等之所惱害，唯除宿世定惡業因現在應熟，或轉重惡現世輕受。憍尸迦！是善男子、善女人等，由此般若波羅蜜多甚深經典大威神力，獲如是等現世種種功德勝利，謂諸天等已發無上菩提心者，或依佛法已得殊勝利樂事者，敬重法故常隨守護增其勢力。何以故？憍尸迦！是善男子、善女人等已發無上正等覺心，恒為救拔諸有情故，恒為成熟諸有情故，恒為不捨諸有情故，恒為利樂諸有情故。彼諸天等亦復如是，由此因緣常來擁護，令諸災橫不能侵惱。」

### 星系 09 · Great Prajna Par

- Core: **大般若波罗蜜多经 · 卷112** T0220
- Unit type: `juan`; cluster units: `20`; unit segments: `137`; centroid sim: `0.9862`
- Gloss coverage in sampled unit: `0/137`
- Samples:
  - `pos 14245 / T0220-CBETA-14245` 「慶喜當知！以獨覺菩提無二為方便、無生為...
    - text: 「慶喜當知！以獨覺菩提無二為方便、無生為方便、無所得為方便，迴向一切智智，修習布施、淨戒、安忍、精進、靜慮、般若波羅蜜多。
  - `pos 14246 / T0220-CBETA-14246` 「慶喜當知！以獨覺菩提無二為方便、無生為...
    - text: 「慶喜當知！以獨覺菩提無二為方便、無生為方便、無所得為方便，迴向一切智智，安住內空、外空、內外空、空空、大空、勝義空、有為空、無為空、畢竟空、無際空、散空、無變異空、本性空、自相空、共相空、一切法空、不可得空、無性空、自性空、無性自性空。
  - `pos 14247 / T0220-CBETA-14247` 「慶喜當知！以獨覺菩提無二為方便、無生為...
    - text: 「慶喜當知！以獨覺菩提無二為方便、無生為方便、無所得為方便，迴向一切智智，安住真如、法界、法性、不虛妄性、不變異性、平等性、離生性、法定、法住、實際、虛空界、不思議界。
  - `pos 14312 / T0220-CBETA-14312` 「世尊！云何以受、想、行、識無二為方便、...
    - text: 「世尊！云何以受、想、行、識無二為方便、無生為方便、無所得為方便，迴向一切智智，修習八解脫、八勝處、九次第定、十遍處？」
  - `pos 14313 / T0220-CBETA-14313` 「慶喜！受、想、行、識，受、想、行、識性...
    - text: 「慶喜！受、想、行、識，受、想、行、識性空。何以故？以受、想、行、識性空與八解脫、八勝處、九次第定、十遍處無二無二分故。慶喜！由此故說：以色等無二為方便、無生為方便、無所得為方便，迴向一切智智，修習八解脫、八勝處、九次第定、十遍處。」
  - `pos 14314 / T0220-CBETA-14314` 「世尊！云何以色無二為方便、無生為方便、...
    - text: 「世尊！云何以色無二為方便、無生為方便、無所得為方便，迴向一切智智，修習四念住、四正斷、四神足、五根、五力、七等覺支、八聖道支？」
  - `pos 14379 / T0220-CBETA-14379` 「慶喜！色處，色處性空。何以故？以色處性...
    - text: 「慶喜！色處，色處性空。何以故？以色處性空與彼苦、集、滅、道聖諦無二無二分故。」
  - `pos 14380 / T0220-CBETA-14380` 「世尊！云何以聲、香、味、觸、法處無二為...
    - text: 「世尊！云何以聲、香、味、觸、法處無二為方便、無生為方便、無所得為方便，迴向一切智智，安住苦、集、滅、道聖諦？」
  - `pos 14381 / T0220-CBETA-14381` 「慶喜！聲、香、味、觸、法處，聲、香、味...
    - text: 「慶喜！聲、香、味、觸、法處，聲、香、味、觸、法處性空。何以故？以聲、香、味、觸、法處性空與彼苦、集、滅、道聖諦無二無二分故。慶喜！由此故說：以色處等無二為方便、無生為方便、無所得為方便，迴向一切智智，安住苦、集、滅、道聖諦。」

## 巴利 (trad-pali)

### 星系 07 · Dīgha Nikāya 121 / Aṅguttara Nikāya

- Core: **Dīgha Nikāya 16 (DN 1210315042)** DN 1210315042
- Unit type: `work`; cluster units: `479`; unit segments: `1664`; centroid sim: `0.9871`
- Gloss coverage in sampled unit: `1569/1664`
- Samples:
  - `pos 1 / DN 1210315042-PLAIN-001` Dīgha Nikāya 16
    - text: Dīgha Nikāya 16
    - gloss: Long Discourses 16
  - `pos 2 / DN 1210315042-PLAIN-002` Mahāparinibbānasutta
    - text: Mahāparinibbānasutta
    - gloss: The Great Discourse on the Buddha’s Extinguishment
  - `pos 3 / DN 1210315042-PLAIN-003` Evaṁ me sutaṁ—
    - text: Evaṁ me sutaṁ—
    - gloss: So I have heard.
  - `pos 832 / DN 1210315042-PLAIN-832` “iti sīlaṁ, iti samādhi, it...
    - text: “iti sīlaṁ, iti samādhi, iti paññā.
    - gloss: “Such is ethics, such is immersion, such is wisdom.
  - `pos 833 / DN 1210315042-PLAIN-833` Sīlaparibhāvito samādhi mah...
    - text: Sīlaparibhāvito samādhi mahapphalo hoti mahānisaṁso.
    - gloss: When immersion is imbued with ethics it’s very fruitful and beneficial.
  - `pos 834 / DN 1210315042-PLAIN-834` Samādhiparibhāvitā paññā ma...
    - text: Samādhiparibhāvitā paññā mahapphalā hoti mahānisaṁsā.
    - gloss: When wisdom is imbued with immersion it’s very fruitful and beneficial.
  - `pos 1662 / DN 1210315042-PLAIN-1662` Devā hariṁsu ekekaṁ,
    - text: Devā hariṁsu ekekaṁ,
    - gloss: were carried off individually by gods
  - `pos 1663 / DN 1210315042-PLAIN-1663` cakkavāḷaparamparāti.
    - text: cakkavāḷaparamparāti.
    - gloss: across the universe.
  - `pos 1664 / DN 1210315042-PLAIN-1664` Mahāparinibbānasuttaṁ niṭṭh...
    - text: Mahāparinibbānasuttaṁ niṭṭhitaṁ tatiyaṁ.

### 星系 11 · Majjhima Nikāya  / Majjhima Nikāya 

- Core: **Majjhima Nikāya 51 (MN 2695410593)** MN 2695410593
- Unit type: `work`; cluster units: `466`; unit segments: `190`; centroid sim: `0.9751`
- Gloss coverage in sampled unit: `181/190`
- Samples:
  - `pos 1 / MN 2695410593-PLAIN-001` Majjhima Nikāya 51
    - text: Majjhima Nikāya 51
    - gloss: Middle Discourses 51
  - `pos 2 / MN 2695410593-PLAIN-002` Kandarakasutta
    - text: Kandarakasutta
    - gloss: With Kandaraka
  - `pos 3 / MN 2695410593-PLAIN-003` Evaṁ me sutaṁ—
    - text: Evaṁ me sutaṁ—
    - gloss: So I have heard.
  - `pos 95 / MN 2695410593-PLAIN-095` ukkuṭikopi hoti ukkuṭikappa...
    - text: ukkuṭikopi hoti ukkuṭikappadhānamanuyutto,
    - gloss: They squat, committed to the endeavor of squatting.
  - `pos 96 / MN 2695410593-PLAIN-096` kaṇṭakāpassayikopi hoti kaṇ...
    - text: kaṇṭakāpassayikopi hoti kaṇṭakāpassaye seyyaṁ kappeti;
    - gloss: They lie on a mat of thorns, making a mat of thorns their bed.
  - `pos 97 / MN 2695410593-PLAIN-097` sāyatatiyakampi udakorohanā...
    - text: sāyatatiyakampi udakorohanānuyogamanuyutto viharati—
    - gloss: They’re devoted to ritual bathing three times a day, including at dusk.
  - `pos 188 / MN 2695410593-PLAIN-188` Idamavoca bhagavā.
    - text: Idamavoca bhagavā.
    - gloss: That is what the Buddha said.
  - `pos 189 / MN 2695410593-PLAIN-189` Attamanā te bhikkhū bhagava...
    - text: Attamanā te bhikkhū bhagavato bhāsitaṁ abhinandunti.
    - gloss: Satisfied, the mendicants approved what the Buddha said.
  - `pos 190 / MN 2695410593-PLAIN-190` Kandarakasuttaṁ niṭṭhitaṁ p...
    - text: Kandarakasuttaṁ niṭṭhitaṁ paṭhamaṁ.

### 星系 09 · Aṅguttara Nikāya / Saṁyutta Nikāya 

- Core: **Aṅguttara Nikāya 2 (AN 2078590569)** AN 2078590569
- Unit type: `work`; cluster units: `437`; unit segments: `125`; centroid sim: `0.961`
- Gloss coverage in sampled unit: `99/125`
- Samples:
  - `pos 1 / AN 2078590569-PLAIN-001` Aṅguttara Nikāya 2
    - text: Aṅguttara Nikāya 2
    - gloss: Numbered Discourses 2.1–10
  - `pos 2 / AN 2078590569-PLAIN-002` 1. Kammakaraṇavagga
    - text: 1. Kammakaraṇavagga
    - gloss: The Chapter on Punishments
  - `pos 3 / AN 2078590569-PLAIN-003` 1. Vajjasutta
    - text: 1. Vajjasutta
    - gloss: 1. Faults
  - `pos 62 / AN 2078590569-PLAIN-062` manosucaritaṁ kataṁ hoti, a...
    - text: manosucaritaṁ kataṁ hoti, akataṁ hoti manoduccaritaṁ.
  - `pos 63 / AN 2078590569-PLAIN-063` So ‘kāyasucaritaṁ me katan’...
    - text: So ‘kāyasucaritaṁ me katan’ti na tappati, ‘akataṁ me kāyaduccaritan’ti na tappati;
    - gloss: Thinking, ‘I’ve done good things by way of body, speech, and mind’, they’re not mortified. Thinking, ‘I haven’t done bad things by way of body, speech, and mind’, they’re not mortified.
  - `pos 64 / AN 2078590569-PLAIN-064` ‘vacīsucaritaṁ me katan’ti...
    - text: ‘vacīsucaritaṁ me katan’ti na tappati, ‘akataṁ me vacīduccaritan’ti na tappati;
  - `pos 123 / AN 2078590569-PLAIN-123` Upaññātena pañcamaṁ;
    - text: Upaññātena pañcamaṁ;
  - `pos 124 / AN 2078590569-PLAIN-124` Saṁyojanañca kaṇhañca,
    - text: Saṁyojanañca kaṇhañca,
  - `pos 125 / AN 2078590569-PLAIN-125` Sukkaṁ cariyā vassūpanāyike...
    - text: Sukkaṁ cariyā vassūpanāyikena vaggo.

### 星系 08 · Dīgha Nikāya 303 / Dīgha Nikāya 217

- Core: **Dīgha Nikāya 33 (DN 303625521)** DN 303625521
- Unit type: `work`; cluster units: `354`; unit segments: `1167`; centroid sim: `0.9766`
- Gloss coverage in sampled unit: `1129/1167`
- Samples:
  - `pos 1 / DN 303625521-PLAIN-001` Dīgha Nikāya 33
    - text: Dīgha Nikāya 33
    - gloss: Long Discourses 33
  - `pos 2 / DN 303625521-PLAIN-002` Saṅgītisutta
    - text: Saṅgītisutta
    - gloss: Reciting in Concert
  - `pos 3 / DN 303625521-PLAIN-003` Evaṁ me sutaṁ—
    - text: Evaṁ me sutaṁ—
    - gloss: So I have heard.
  - `pos 583 / DN 303625521-PLAIN-583` Ye ca rūpapaccayā uppajjant...
    - text: Ye ca rūpapaccayā uppajjanti āsavā vighātā pariḷāhā, mutto so tehi, na so taṁ vedanaṁ vedeti.
    - gloss: They’re freed from the distressing and feverish defilements that arise because of form, so they don’t experience that kind of feeling.
  - `pos 584 / DN 303625521-PLAIN-584` Idamakkhātaṁ rūpānaṁ nissar...
    - text: Idamakkhātaṁ rūpānaṁ nissaraṇaṁ.
    - gloss: This is how the escape from forms is explained.
  - `pos 585 / DN 303625521-PLAIN-585` Puna caparaṁ, āvuso, bhikkh...
    - text: Puna caparaṁ, āvuso, bhikkhuno sakkāyaṁ manasikaroto sakkāye cittaṁ na pakkhandati na pasīdati na santiṭṭhati na vimuccati.
    - gloss: Take a case where a mendicant focuses on substantial reality, but their mind does not leap forth, gain confidence, settle down, and become decided.
  - `pos 1165 / DN 303625521-PLAIN-1165` Idamavocāyasmā sāriputto, s...
    - text: Idamavocāyasmā sāriputto, samanuñño satthā ahosi.
    - gloss: That is what Venerable Sāriputta said, and the teacher approved.
  - `pos 1166 / DN 303625521-PLAIN-1166` Attamanā te bhikkhū āyasmat...
    - text: Attamanā te bhikkhū āyasmato sāriputtassa bhāsitaṁ abhinandunti.
    - gloss: Satisfied, the mendicants approved what Sāriputta said.
  - `pos 1167 / DN 303625521-PLAIN-1167` Saṅgītisuttaṁ niṭṭhitaṁ das...
    - text: Saṅgītisuttaṁ niṭṭhitaṁ dasamaṁ.

### 星系 02 · Saṁyutta Nikāya  / Dīgha Nikāya 187

- Core: **Saṁyutta Nikāya 45.34 (SN 3368259234)** SN 3368259234
- Unit type: `work`; cluster units: `331`; unit segments: `33`; centroid sim: `0.9757`
- Gloss coverage in sampled unit: `32/33`
- Samples:
  - `pos 1 / SN 3368259234-PLAIN-001` Saṁyutta Nikāya 45.34
    - text: Saṁyutta Nikāya 45.34
    - gloss: Linked Discourses 45.34
  - `pos 2 / SN 3368259234-PLAIN-002` 4. Paṭipattivagga
    - text: 4. Paṭipattivagga
    - gloss: 4. Practice
  - `pos 3 / SN 3368259234-PLAIN-003` Pāraṅgamasutta
    - text: Pāraṅgamasutta
    - gloss: Going to the Far Shore
  - `pos 16 / SN 3368259234-PLAIN-016` dhamme dhammānuvattino;
    - text: dhamme dhammānuvattino;
    - gloss: those who practice accordingly
  - `pos 17 / SN 3368259234-PLAIN-017` Te janā pāramessanti,
    - text: Te janā pāramessanti,
    - gloss: are the ones who will cross over
  - `pos 18 / SN 3368259234-PLAIN-018` maccudheyyaṁ suduttaraṁ.
    - text: maccudheyyaṁ suduttaraṁ.
    - gloss: Death’s dominion so hard to pass.
  - `pos 31 / SN 3368259234-PLAIN-031` Khīṇāsavā jutimanto,
    - text: Khīṇāsavā jutimanto,
    - gloss: With defilements ended, brilliant,
  - `pos 32 / SN 3368259234-PLAIN-032` te loke parinibbutā”ti.
    - text: te loke parinibbutā”ti.
    - gloss: they are quenched in this world.”
  - `pos 33 / SN 3368259234-PLAIN-033` Catutthaṁ.
    - text: Catutthaṁ.

### 星系 12 · Aṅguttara Nikāya / Saṁyutta Nikāya 

- Core: **Aṅguttara Nikāya 5.109 (AN 3784702361)** AN 3784702361
- Unit type: `work`; cluster units: `331`; unit segments: `12`; centroid sim: `0.9507`
- Gloss coverage in sampled unit: `11/12`
- Samples:
  - `pos 1 / AN 3784702361-PLAIN-001` Aṅguttara Nikāya 5.109
    - text: Aṅguttara Nikāya 5.109
    - gloss: Numbered Discourses 5.109
  - `pos 2 / AN 3784702361-PLAIN-002` 11. Phāsuvihāravagga
    - text: 11. Phāsuvihāravagga
    - gloss: 11. Living Comfortably
  - `pos 3 / AN 3784702361-PLAIN-003` Cātuddisasutta
    - text: Cātuddisasutta
    - gloss: All Four Quarters
  - `pos 6 / AN 3784702361-PLAIN-006` Idha, bhikkhave, bhikkhu sī...
    - text: Idha, bhikkhave, bhikkhu sīlavā hoti, pātimokkhasaṁvarasaṁvuto viharati ācāragocarasampanno aṇumattesu vajjesu bhayadassāvī, samādāya sikkhati sikkhāpadesu;
    - gloss: It’s when mendicant is ethical, restrained in the monastic code, conducting themselves well and resorting for alms in suitable places. Seeing danger in the slightest fault, they keep the rules they’ve undertaken.
  - `pos 7 / AN 3784702361-PLAIN-007` bahussuto hoti sutadharo su...
    - text: bahussuto hoti sutadharo sutasannicayo, ye te dhammā ādikalyāṇā majjhekalyāṇā pariyosānakalyāṇā sātthaṁ sabyañjanaṁ kevalaparipuṇṇaṁ parisuddhaṁ brahmacariyaṁ abhivadanti, tathārūpāssa dhammā bahussutā honti dhātā vacasā paricitā manasānupekkhitā diṭṭhiyā suppaṭividdhā;
    - gloss: They’re very learned, remembering and keeping what they’ve learned. These teachings are good in the beginning, good in the middle, and good in the end, meaningful and well-phrased, describing a spiritual practice that’s entirely full and pure. They are very learned in such teachings, remembering them, rehearsing them, mentally scrutinizing them, and penetrat...
  - `pos 8 / AN 3784702361-PLAIN-008` santuṭṭho hoti itarītaracīv...
    - text: santuṭṭho hoti itarītaracīvarapiṇḍapātasenāsanagilānappaccayabhesajjaparikkhārena;
    - gloss: They’re content with any kind of robes, almsfood, lodgings, and medicines and supplies for the sick.
  - `pos 10 / AN 3784702361-PLAIN-010` āsavānaṁ khayā anāsavaṁ cet...
    - text: āsavānaṁ khayā anāsavaṁ cetovimuttiṁ paññāvimuttiṁ diṭṭheva dhamme sayaṁ abhiññā sacchikatvā upasampajja viharati.
    - gloss: They realize the undefiled freedom of heart and freedom by wisdom in this very life. And they live having realized it with their own insight due to the ending of defilements.
  - `pos 11 / AN 3784702361-PLAIN-011` Imehi, kho, bhikkhave, pañc...
    - text: Imehi, kho, bhikkhave, pañcahi dhammehi samannāgato bhikkhu cātuddiso hotī”ti.
    - gloss: A mendicant with these five qualities is at ease in any quarter.”
  - `pos 12 / AN 3784702361-PLAIN-012` Navamaṁ.
    - text: Navamaṁ.

### 星系 05 · Saṁyutta Nikāya  / Saṁyutta Nikāya 

- Core: **Saṁyutta Nikāya 24.96 (SN 1807744006)** SN 1807744006
- Unit type: `work`; cluster units: `330`; unit segments: `47`; centroid sim: `0.972`
- Gloss coverage in sampled unit: `41/47`
- Samples:
  - `pos 1 / SN 1807744006-PLAIN-001` Saṁyutta Nikāya 24.96
    - text: Saṁyutta Nikāya 24.96
    - gloss: Linked Discourses 24.96
  - `pos 2 / SN 1807744006-PLAIN-002` 4. Catutthagamanavagga
    - text: 4. Catutthagamanavagga
    - gloss: 4. The Fourth Round
  - `pos 3 / SN 1807744006-PLAIN-003` Adukkhamasukhīsutta
    - text: Adukkhamasukhīsutta
    - gloss: The Self Is Neither Happy Nor Suffering
  - `pos 23 / SN 1807744006-PLAIN-023` “Vedanā …
    - text: “Vedanā …
    - gloss: “Is feeling …
  - `pos 24 / SN 1807744006-PLAIN-024` saññā …
    - text: saññā …
    - gloss: perception …
  - `pos 25 / SN 1807744006-PLAIN-025` saṅkhārā …
    - text: saṅkhārā …
    - gloss: choices …
  - `pos 45 / SN 1807744006-PLAIN-045` Tatiyagamane chabbīsaṁ vitt...
    - text: Tatiyagamane chabbīsaṁ vitthāretabbāni,
  - `pos 46 / SN 1807744006-PLAIN-046` Catutthagamane chabbīsaṁ vi...
    - text: Catutthagamane chabbīsaṁ vitthāretabbāni.
  - `pos 47 / SN 1807744006-PLAIN-047` Diṭṭhisaṁyuttaṁ samattaṁ.
    - text: Diṭṭhisaṁyuttaṁ samattaṁ.
    - gloss: The Linked Discourses on views are complete.

### 星系 04 · Dīgha Nikāya 155 / Majjhima Nikāya 

- Core: **Dīgha Nikāya 21 (DN 1555713017)** DN 1555713017
- Unit type: `work`; cluster units: `270`; unit segments: `515`; centroid sim: `0.979`
- Gloss coverage in sampled unit: `475/515`
- Samples:
  - `pos 1 / DN 1555713017-PLAIN-001` Dīgha Nikāya 21
    - text: Dīgha Nikāya 21
    - gloss: Long Discourses 21
  - `pos 2 / DN 1555713017-PLAIN-002` Sakkapañhasutta
    - text: Sakkapañhasutta
    - gloss: Sakka’s Questions
  - `pos 3 / DN 1555713017-PLAIN-003` Evaṁ me sutaṁ—
    - text: Evaṁ me sutaṁ—
    - gloss: So I have heard.
  - `pos 257 / DN 1555713017-PLAIN-257` Attamano sakko devānamindo...
    - text: Attamano sakko devānamindo bhagavato bhāsitaṁ abhinandi anumodi:
    - gloss: Delighted, Sakka approved and agreed with what the Buddha said, saying,
  - `pos 258 / DN 1555713017-PLAIN-258` “evametaṁ, bhagavā, evameta...
    - text: “evametaṁ, bhagavā, evametaṁ, sugata.
    - gloss: “That’s so true, Blessed One! That’s so true, Holy One!
  - `pos 259 / DN 1555713017-PLAIN-259` Tiṇṇā mettha kaṅkhā vigatā...
    - text: Tiṇṇā mettha kaṅkhā vigatā kathaṅkathā bhagavato pañhaveyyākaraṇaṁ sutvā”ti.
    - gloss: Hearing the Buddha’s answer, I’ve gone beyond doubt and got rid of indecision.”
  - `pos 513 / DN 1555713017-PLAIN-513` iti ye sakkena devānaminden...
    - text: iti ye sakkena devānamindena ajjhiṭṭhapañhā puṭṭhā, te bhagavatā byākatā.
    - gloss: Such were the questions Sakka was invited to ask, and which were answered by the Buddha.
  - `pos 514 / DN 1555713017-PLAIN-514` Tasmā imassa veyyākaraṇassa...
    - text: Tasmā imassa veyyākaraṇassa sakkapañhātveva adhivacananti.
    - gloss: And that’s why the name of this discussion is “Sakka’s Questions”.
  - `pos 515 / DN 1555713017-PLAIN-515` Sakkapañhasuttaṁ niṭṭhitaṁ...
    - text: Sakkapañhasuttaṁ niṭṭhitaṁ aṭṭhamaṁ.

### 星系 06 · Saṁyutta Nikāya  / Saṁyutta Nikāya 

- Core: **Saṁyutta Nikāya 22.40 (SN 3057819795)** SN 3057819795
- Unit type: `work`; cluster units: `268`; unit segments: `7`; centroid sim: `0.9492`
- Gloss coverage in sampled unit: `6/7`
- Samples:
  - `pos 1 / SN 3057819795-PLAIN-001` Saṁyutta Nikāya 22.40
    - text: Saṁyutta Nikāya 22.40
    - gloss: Linked Discourses 22.40
  - `pos 2 / SN 3057819795-PLAIN-002` 4. Natumhākavagga
    - text: 4. Natumhākavagga
    - gloss: 4. It’s Not Yours
  - `pos 3 / SN 3057819795-PLAIN-003` Dutiyaanudhammasutta
    - text: Dutiyaanudhammasutta
    - gloss: In Line With the Teaching (2nd)
  - `pos 4 / SN 3057819795-PLAIN-004` Sāvatthinidānaṁ.
    - text: Sāvatthinidānaṁ.
    - gloss: At Sāvatthī.
  - `pos 5 / SN 3057819795-PLAIN-005` “Dhammānudhammappaṭipannass...
    - text: “Dhammānudhammappaṭipannassa, bhikkhave, bhikkhuno ayamanudhammo hoti yaṁ rūpe aniccānupassī vihareyya …pe…
    - gloss: “Mendicants, when a mendicant is practicing in line with the teaching, this is what’s in line with the teaching. They should meditate observing impermanence in form, feeling, perception, choices, and consciousness. …
  - `pos 6 / SN 3057819795-PLAIN-006` ‘parimuccati dukkhasmā’ti v...
    - text: ‘parimuccati dukkhasmā’ti vadāmī”ti.
    - gloss: They’re freed from suffering, I say.”
  - `pos 7 / SN 3057819795-PLAIN-007` Aṭṭhamaṁ.
    - text: Aṭṭhamaṁ.

### 星系 01 · Saṁyutta Nikāya  / Aṅguttara Nikāya

- Core: **Saṁyutta Nikāya 12.30 (SN 3531872024)** SN 3531872024
- Unit type: `work`; cluster units: `131`; unit segments: `35`; centroid sim: `0.9648`
- Gloss coverage in sampled unit: `27/35`
- Samples:
  - `pos 1 / SN 3531872024-PLAIN-001` Saṁyutta Nikāya 12.30
    - text: Saṁyutta Nikāya 12.30
    - gloss: Linked Discourses 12.30
  - `pos 2 / SN 3531872024-PLAIN-002` 3. Dasabalavagga
    - text: 3. Dasabalavagga
    - gloss: 3. The Ten Powers
  - `pos 3 / SN 3531872024-PLAIN-003` Dutiyasamaṇabrāhmaṇasutta
    - text: Dutiyasamaṇabrāhmaṇasutta
    - gloss: Ascetics and Brahmins (2nd)
  - `pos 17 / SN 3531872024-PLAIN-017` Ye ca kho keci, bhikkhave,...
    - text: Ye ca kho keci, bhikkhave, samaṇā vā brāhmaṇā vā jarāmaraṇaṁ pajānanti, jarāmaraṇasamudayaṁ pajānanti, jarāmaraṇanirodhaṁ pajānanti, jarāmaraṇanirodhagāminiṁ paṭipadaṁ pajānanti te vata jarāmaraṇaṁ samatikkamma ṭhassantīti ṭhānametaṁ vijjati.
    - gloss: There are ascetics and brahmins who do understand old age and death, their origin, their cessation, and the practice that leads to their cessation. It’s possible that they will abide having transcended old age and death.
  - `pos 18 / SN 3531872024-PLAIN-018` Jātiṁ pajānanti …pe…
    - text: Jātiṁ pajānanti …pe…
    - gloss: They understand rebirth …
  - `pos 19 / SN 3531872024-PLAIN-019` bhavaṁ …
    - text: bhavaṁ …
    - gloss: continued existence …
  - `pos 33 / SN 3531872024-PLAIN-033` Aññatitthiyabhūmijo;
    - text: Aññatitthiyabhūmijo;
  - `pos 34 / SN 3531872024-PLAIN-034` Upavāṇo paccayo bhikkhu,
    - text: Upavāṇo paccayo bhikkhu,
  - `pos 35 / SN 3531872024-PLAIN-035` Dve ca samaṇabrāhmaṇāti.
    - text: Dve ca samaṇabrāhmaṇāti.

### 星系 10 · Aṅguttara Nikāya / Aṅguttara Nikāya

- Core: **Aṅguttara Nikāya 10 (AN 540731749)** AN 540731749
- Unit type: `work`; cluster units: `20`; unit segments: `7`; centroid sim: `0.9754`
- Gloss coverage in sampled unit: `7/7`
- Samples:
  - `pos 1 / AN 540731749-PLAIN-001` Aṅguttara Nikāya 10
    - text: Aṅguttara Nikāya 10
    - gloss: Numbered Discourses 10.238
  - `pos 2 / AN 540731749-PLAIN-002` 23. Rāgapeyyāla
    - text: 23. Rāgapeyyāla
    - gloss: 23. Abbreviated Texts Beginning With Greed
  - `pos 3 / AN 540731749-PLAIN-003` ~
    - text: ~
    - gloss: Untitled Discourse on Greed (2nd)
  - `pos 4 / AN 540731749-PLAIN-004` “Rāgassa, bhikkhave, abhiññ...
    - text: “Rāgassa, bhikkhave, abhiññāya dasa dhammā bhāvetabbā.
    - gloss: “For insight into greed, ten things should be developed.
  - `pos 5 / AN 540731749-PLAIN-005` Katame dasa?
    - text: Katame dasa?
    - gloss: What ten?
  - `pos 6 / AN 540731749-PLAIN-006` Aniccasaññā, anattasaññā, ā...
    - text: Aniccasaññā, anattasaññā, āhāre paṭikūlasaññā, sabbaloke anabhiratasaññā, aṭṭhikasaññā, puḷavakasaññā, vinīlakasaññā, vipubbakasaññā, vicchiddakasaññā, uddhumātakasaññā—
    - gloss: The perceptions of impermanence, not-self, repulsiveness of food, dissatisfaction with the whole world, a skeleton, a worm-infested corpse, a livid corpse, a festering corpse, a split open corpse, and a bloated corpse.
  - `pos 7 / AN 540731749-PLAIN-007` rāgassa, bhikkhave, abhiññā...
    - text: rāgassa, bhikkhave, abhiññāya ime dasa dhammā bhāvetabbā”ti.
    - gloss: For insight into greed, these ten things should be developed.”

### 星系 03 · Aṅguttara Nikāya / Aṅguttara Nikāya

- Core: **Aṅguttara Nikāya 10.34 (AN 553313500)** AN 553313500
- Unit type: `work`; cluster units: `4`; unit segments: `18`; centroid sim: `1.0`
- Gloss coverage in sampled unit: `17/18`
- Samples:
  - `pos 1 / AN 553313500-PLAIN-001` Aṅguttara Nikāya 10.34
    - text: Aṅguttara Nikāya 10.34
    - gloss: Numbered Discourses 10.34
  - `pos 2 / AN 553313500-PLAIN-002` 4. Upālivagga
    - text: 4. Upālivagga
    - gloss: 4. With Upāli
  - `pos 3 / AN 553313500-PLAIN-003` Upasampadāsutta
    - text: Upasampadāsutta
    - gloss: Ordination
  - `pos 9 / AN 553313500-PLAIN-009` pātimokkhaṁ kho panassa vit...
    - text: pātimokkhaṁ kho panassa vitthārena svāgataṁ hoti suvibhattaṁ suppavattaṁ suvinicchitaṁ suttaso anubyañjanaso;
    - gloss: Both monastic codes have been passed down to them in detail, well analyzed, well mastered, well evaluated in both the rules and accompanying material.
  - `pos 10 / AN 553313500-PLAIN-010` paṭibalo hoti gilānaṁ upaṭṭ...
    - text: paṭibalo hoti gilānaṁ upaṭṭhātuṁ vā upaṭṭhāpetuṁ vā;
    - gloss: They’re able to care for the sick or get someone else to do so.
  - `pos 11 / AN 553313500-PLAIN-011` paṭibalo hoti anabhiratiṁ v...
    - text: paṭibalo hoti anabhiratiṁ vūpakāsetuṁ vā vūpakāsāpetuṁ vā;
    - gloss: They’re able to settle dissatisfaction or get someone else to do so.
  - `pos 16 / AN 553313500-PLAIN-016` paṭibalo hoti adhipaññāya s...
    - text: paṭibalo hoti adhipaññāya samādapetuṁ.
    - gloss: and the higher wisdom.
  - `pos 17 / AN 553313500-PLAIN-017` Imehi kho, upāli, dasahi dh...
    - text: Imehi kho, upāli, dasahi dhammehi samannāgatena bhikkhunā upasampādetabban”ti.
    - gloss: A mendicant should possess these ten qualities to give ordination.”
  - `pos 18 / AN 553313500-PLAIN-018` Catutthaṁ.
    - text: Catutthaṁ.

## 藏传 (trad-tibetan)

### 星系 05 · The Absorption T / The Basket’s Dis

- Core: **The Good Eon · section 010** Toh 94
- Unit type: `section-window`; cluster units: `419`; unit segments: `120`; centroid sim: `0.9923`
- Gloss coverage in sampled unit: `120/120`
- Samples:
  - `pos 1081 / Toh 94-PLAIN-1081` དེ་བཞིན་གཤེགས་པའི་ལམ་གཏེར་ས...
    - text: དེ་བཞིན་གཤེགས་པའི་ལམ་གཏེར་སྣ་ཚོགས་པ་སྤོབས་པ་ཕྱིན་ཅི་མ་ལོག་པ་ཕྱག་རྒྱ་དགེ་བའི་རྩ་བ་ལེགས་པར་སྡུད་པའི་རྒྱ་མཚོ་གཟུངས་ཀྱི་རིགས་བདུད་ཟིལ་གྱིས་གནོན་པ་ཐམས་ཅད་མཁྱེན་པ་ཉིད་དུ་བསྒྲུབ་པ་ལ་རྗེས་སུ་རྟོགས་པའི་མདོ་སྡེ་འདི་དང་འདི་ལྟ་བུ་དག་བྲིས་ནས་འཆང་བ་དང་སྟོན་པར་བགྱིད་ལགས་སོ། །
    - gloss: The path of the thus-gone ones, the seal of the flawless rich treasures of eloquence, the ocean that brings together the roots of virtue, and the retentions that subdue the māras and accomplish omniscience are conveyed in discourses such as this one. We hereby pledge to write them down, carry them, and teach them at that time.
  - `pos 1082 / Toh 94-PLAIN-1082` བཅོམ་ལྡན་འདས་བདག་ཅག་སེམས་ཅན...
    - text: བཅོམ་ལྡན་འདས་བདག་ཅག་སེམས་ཅན་དམྱལ་བ་ན་མཆིས་སུ་ལགས་ཀྱང་། ཏིང་ངེ་འཛིན་རིན་པོ་ཆེ་འདིའི་སླད་དུ་ནི་སྤྲོ་བར་བགྱིད་ལགས་སོ། །
    - gloss: Blessed One, even if it means living in hell, we shall do so happily for the sake of this precious absorption.”
  - `pos 1083 / Toh 94-PLAIN-1083` དེ་ནས་བྱང་ཆུབ་སེམས་དཔའ་མཆོག...
    - text: དེ་ནས་བྱང་ཆུབ་སེམས་དཔའ་མཆོག་ཏུ་དགའ་བའི་རྒྱལ་པོས་དེའི་ཚེ་ཚིགས་སུ་བཅད་པ་འདི་དག་གསོལ་ཏོ། །
    - gloss: The bodhisattva Prāmodyarāja then offered these verses:
  - `pos 1140 / Toh 94-PLAIN-1140` དགེ་བའི་རྩ་བ་དེ་བྱས་པས་ཆོས་...
    - text: དགེ་བའི་རྩ་བ་དེ་བྱས་པས་ཆོས་སྨྲ་བ་དང་། རྒྱལ་པོ་བུ་དང་བཅས་ཤིང་སྐྱེ་བོའི་འཁོར་དང་བཅས་པ་དང་། ཚོགས་པ་ཐམས་ཅད་ཀྱིས་བསྐལ་པ་བརྒྱད་ཅུར་སངས་རྒྱས་གཏམས་པ་བྱེ་བ་སུམ་ཁྲི་མཉེས་པར་བྱས་ཏེ
    - gloss: Due to the roots of virtue resulting from this, the Dharma teacher, the king, his sons, and all the other people involved came together to please three billion buddhas over a period of eighty eons,
  - `pos 1141 / Toh 94-PLAIN-1141` ཐམས་ཅད་ལས་ཏིང་ངེ་འཛིན་འདི་ཐ...
    - text: ཐམས་ཅད་ལས་ཏིང་ངེ་འཛིན་འདི་ཐོབ་བོ། །
    - gloss: and they received this absorption from each of them.
  - `pos 1142 / Toh 94-PLAIN-1142` བསམ་པ་ཇི་ལྟ་བ་བཞིན་དུ་སངས་ར...
    - text: བསམ་པ་ཇི་ལྟ་བ་བཞིན་དུ་སངས་རྒྱས་ཀྱི་ཞིང་ཡང་ཡོངས་སུ་འཛིན་པར་གྱུར་ཏོ། །
    - gloss: In accordance with their wishes, they also took up residence in buddha realms.
  - `pos 1198 / Toh 94-PLAIN-1198` དེ་ནས་ཚེ་དང་ལྡན་པ་ཤཱ་རིའི་བ...
    - text: དེ་ནས་ཚེ་དང་ལྡན་པ་ཤཱ་རིའི་བུ་གནས་བརྟན་མཽད་གལ་གྱི་བུ་ཆེན་པོ་ག་ལ་བ་དེར་སོང་སྟེ།
    - gloss: The venerable Śāriputra then went to see the venerable Mahā­maudgalyāyana,
  - `pos 1199 / Toh 94-PLAIN-1199` ལིཙྪ་བཱི་རྣམས་ཀྱི་བསམ་པ་དང་...
    - text: ལིཙྪ་བཱི་རྣམས་ཀྱི་བསམ་པ་དང་རང་བཞིན་དེ་ཉིད་སྨྲས་སོ། །
    - gloss: explaining to him about the intents and wishes of the Licchavis.
  - `pos 1200 / Toh 94-PLAIN-1200` དེ་ནས་མཽད་གལ་གྱི་བུ་ཆེན་པོ་...
    - text: དེ་ནས་མཽད་གལ་གྱི་བུ་ཆེན་པོ་རྫུ་འཕྲུལ་གྱི་མཐུས་སྟོང་གསུམ་གྱི་སྟོང་ཆེན་པོའི་འཇིག་རྟེན་གྱི་ཁམས་རྣམས་གཡོས་རབ་ཏུ་གཡོས།
    - gloss: In response, the venerable Mahā­maudgalyāyana applied his miraculous abilities, thus causing the entire trichiliocosm to tremble and shake,

### 星系 01 · The Stem Array / The White Lotus 

- Core: **The Questions of the Kinnara King Druma · section 014** Toh 157
- Unit type: `section-window`; cluster units: `323`; unit segments: `120`; centroid sim: `0.9932`
- Gloss coverage in sampled unit: `120/120`
- Samples:
  - `pos 1561 / Toh 157-PLAIN-1561` དགེ་བ་ཞེས་བྱ་བའི་འཇིག་རྟེན་...
    - text: དགེ་བ་ཞེས་བྱ་བའི་འཇིག་རྟེན་གྱི་ཁམས་དེ་ཡང་བཻ་ཌཱུརྱ་ལས་གྲུབ་པ། རྒྱན་ཐམས་ཅད་ཀྱིས་བརྒྱན་པ། རྣམ་པའི་མཆོག་ཐམས་ཅད་དང་ལྡན་པ་དགའ་ལྡན་གྱི་ལྷའི་རིས་ལྟ་བུར་ཁང་ཁྱིམ་དང་། ལོངས་སྤྱོད་དང་། ཉེ་བར་སྤྱོད་པ་དང་། བཟའ་བ་དང་། བཏུང་བ་བསམས་པ་ཙམ་གྱིས་འབྱོར་པའོ། །
    - gloss: That universe, Śubhā, was made of beryl and adorned with all possible types of ornaments. Just as in the divine abode of the Heaven of Joy, that realm had all the most sublime features, and all houses, possessions, pleasures, food, and beverages manifested just by thinking of them.
  - `pos 1562 / Toh 157-PLAIN-1562` སངས་རྒྱས་ཀྱི་ཞིང་དེ་ན་ཐེག་པ...
    - text: སངས་རྒྱས་ཀྱི་ཞིང་དེ་ན་ཐེག་པ་ཆེན་པོ་མ་གཏོགས་པར་ཐེག་པ་གཞན་རྣམ་པར་གཞག་པ་མེད་པར་གྱུར་ཏོ། །
    - gloss: In that buddha realm, everyone without exception was settled within the Great Vehicle and nowhere else.
  - `pos 1563 / Toh 157-PLAIN-1563` རིགས་ཀྱི་བུ་དེའི་ཚེ་དེའི་དུ...
    - text: རིགས་ཀྱི་བུ་དེའི་ཚེ་དེའི་དུས་ན་གླིང་བཞི་ལ་དབང་བའི་འཁོར་ལོས་སྒྱུར་བའི་རྒྱལ་པོས་འཛིན་ཅེས་བྱ་བ་རིན་པོ་ཆེ་སྣ་བདུན་དང་ལྡན་པ་ཞིག་བྱུང་སྟེ།
    - gloss: “Noble son, at that time, a universal monarch called Nimiṃdhara, who ruled over the four continents and was endowed with the seven precious attributes, appeared in the world.
  - `pos 1620 / Toh 157-PLAIN-1620` དེ་ནས་འདོད་པ་ན་སྤྱོད་པ་དང་།...
    - text: དེ་ནས་འདོད་པ་ན་སྤྱོད་པ་དང་། གཟུགས་ན་སྤྱོད་པ་དང་། གནས་གཙང་མའི་རིས་ཀྱི་ལྷའི་བུ་དེ་དག་དང་། ཀླུ་དང་། གནོད་སྦྱིན་དང་། དྲི་ཟ་དང་། མི་འམ་ཅི་དང་། ལྟོ་འཕྱེ་ཆེན་པོ་དང་། ཐམས་ཅད་དང་ལྡན་པའི་འཁོར་དེ་བཅོམ་ལྡན་འདས་ཀྱིས་ལེགས་པར་གསུངས་པ་ལ་རྗེས་སུ་ཡི་རངས་ནས།
    - gloss: At that moment, the gods of the desire realm, the gods of the form realm, the gods of the pure realms, the nāgas, the yakṣas, the gandharvas, the kiṃnaras, the mahoragas, and the entire retinue rejoiced at the Blessed One’s well-spoken words, and
  - `pos 1621 / Toh 157-PLAIN-1621` ལྷའི་མེ་ཏོག་རྣམ་པ་མང་པོ་ཁ་ད...
    - text: ལྷའི་མེ་ཏོག་རྣམ་པ་མང་པོ་ཁ་དོག་སྣ་ཚོགས་པས་བཅོམ་ལྡན་འདས་ལ་མངོན་པར་གཏོར་ཏོ། །
    - gloss: they showered him with many kinds of multicolored divine flowers.
  - `pos 1622 / Toh 157-PLAIN-1622` དེ་ནས་མི་འམ་ཅིའི་རྒྱལ་པོ་སྡ...
    - text: དེ་ནས་མི་འམ་ཅིའི་རྒྱལ་པོ་སྡོང་པོས་འདི་སྙམ་དུ་བསམས་ཏེ།
    - gloss: The kiṃnara king Druma then thought,
  - `pos 1678 / Toh 157-PLAIN-1678` སངས་རྒྱས་ཡོན་ཏན་བས་པར་འགྱུར...
    - text: སངས་རྒྱས་ཡོན་ཏན་བས་པར་འགྱུར་མི་གདའ། །
    - gloss: your awakened qualities will never be exhausted!”
  - `pos 1679 / Toh 157-PLAIN-1679` དེ་ནས་བཅོམ་ལྡན་འདས་ཤིང་རྟ་ལ...
    - text: དེ་ནས་བཅོམ་ལྡན་འདས་ཤིང་རྟ་ལ་བཞུགས་ཏེ་ནམ་མཁའི་དཀྱིལ་གྱི་ལམ་ནས་གཤེགས་པས་གཤེགས་ཤིང་། གསེར་གྱི་ཁ་དོག་ལྟ་བུར་སྐུ་ལས་འོད་གང་གིས་སྟོང་གསུམ་གྱི་སྟོང་ཆེན་པོའི་འཇིག་རྟེན་གྱི་ཁམས་ཁྱབ་པར་འགྱུར་བ་དེ་ལྟ་བུའི་འོད་ཕྱུང་བ་དང་། འོད་དེས་རྒྱལ་པོའི་ཁབ་ཀྱི་གྲོང་ཁྱེར་ཆེན་པོ་དང་། བྱ་རྒོད་ཀྱི་ཕུང་པོའི་རི་ཡང་རབ་ཏུ་ཁྱབ་པར་གྱུར་ཏོ། །
    - gloss: The golden-colored body of the Blessed One, as he traveled through the sky sitting in the chariot, shone with light that spread throughout this great trichiliocosm. The light also illuminated the city of Rājagṛha and Vulture Peak Mountain.
  - `pos 1680 / Toh 157-PLAIN-1680` དེ་ནས་བཅོམ་ལྡན་འདས་ཤིང་རྟ་ད...
    - text: དེ་ནས་བཅོམ་ལྡན་འདས་ཤིང་རྟ་དེས་རྒྱལ་པོའི་ཁབ་ཀྱི་གྲོང་ཁྱེར་དང་བྱ་རྒོད་ཀྱི་ཕུང་པོའི་རི་ག་ལ་བ་དེར་གཤེགས་སོ། །
    - gloss: In this way the Blessed One reached the city of Rājagṛha and Vulture Peak Mountain.

### 星系 06 · The Application  / The Precious Dis

- Core: **The Precious Discourse on the Blessed One’s Extensive Wisdom That Leads to Infinite Certainty · section 044** Toh 99
- Unit type: `section-window`; cluster units: `283`; unit segments: `120`; centroid sim: `0.9905`
- Gloss coverage in sampled unit: `120/120`
- Samples:
  - `pos 5161 / Toh 99-PLAIN-5161` ཚུལ་ཁྲིམས་འཆལ་པས་བྱང་ཆུབ་སེ...
    - text: ཚུལ་ཁྲིམས་འཆལ་པས་བྱང་ཆུབ་སེམས་དཔའི་ཚུལ་ཁྲིམས་འཆལ་པར་བྱ་མི་ནུས། ལྟ་བ་ལོག་པས་བྱང་ཆུབ་སེམས་དཔའི་ལྟ་བ་ལོག་པར་བྱ་མི་ནུས་ཀྱི། ཉན་ཐོས་ཀྱི་ཐེག་པ་པ་དང་། རང་སངས་རྒྱས་ཀྱི་ཐེག་པ་པས་ནི་བྱང་ཆུབ་སེམས་དཔའ་ཟག་པ་མེད་པའི་ཤེས་པ་ལ་འཇུག་པར་མི་ནུས་སོ། །
    - gloss: Faulty discipline cannot make a bodhisattva’s discipline faulty, nor can wrong views distort a bodhisattva’s view. However, the adherents of the vehicle of the hearers and the vehicle of the solitary buddhas cannot lead bodhisattvas to undefiled knowledge.
  - `pos 5162 / Toh 99-PLAIN-5162` དེ་ལྟ་བས་ན་ཉན་ཐོས་དང་། རང་ས...
    - text: དེ་ལྟ་བས་ན་ཉན་ཐོས་དང་། རང་སངས་རྒྱས་ཀྱི་ཐེག་པ་པ་ནི་བྱང་ཆུབ་སེམས་དཔའི་སྡིག་པའི་གྲོགས་པོ་ཡིན་ནོ། །
    - gloss: It is for this reason that adherents of the vehicles of hearers and solitary buddhas are a bad influence for bodhisattvas.
  - `pos 5163 / Toh 99-PLAIN-5163` ཡང་བྱང་ཆུབ་སེམས་དཔའི་ཐེག་པ་...
    - text: ཡང་བྱང་ཆུབ་སེམས་དཔའི་ཐེག་པ་ལ་ཡང་དག་པར་གནས་པས་ཚུལ་ཁྲིམས་འཆལ་པའམ། ལྟ་བ་ལོག་པ་དང་ལྷན་ཅིག་དགའ་བར་བྱས་པ་ནི་རུང་གི །ཉན་ཐོས་དང་རང་སངས་རྒྱས་ཀྱི་ཐེག་པ་པ་དག་ནི་དེ་ལྟ་མ་ཡིན་ནོ། །
    - gloss: “Moreover, for those who are well founded in the vehicle of the bodhisattvas, it is permissible to fraternize with people with faulty discipline and distorted ideas, while this is not the case for the vehicles of the hearers and solitary buddhas.
  - `pos 5220 / Toh 99-PLAIN-5220` རྒྱུ་གང་གིས་ཐམས་ཅད་དུ་འགྲོ་...
    - text: རྒྱུ་གང་གིས་ཐམས་ཅད་དུ་འགྲོ་བའི་ལམ་ཤེས་པའི་ལམ་དུ་འགྱུར།
    - gloss: ‘What are the causes of the knowledge of the paths that lead to all destinations?’
  - `pos 5221 / Toh 99-PLAIN-5221` དེ་འདི་སྙམ་དུ་རབ་ཏུ་ཤེས་ཏེ།
    - text: དེ་འདི་སྙམ་དུ་རབ་ཏུ་ཤེས་ཏེ།
    - gloss: Thinking further, he realized,
  - `pos 5222 / Toh 99-PLAIN-5222` ཐམས་ཅད་དུ་འགྲོ་བའི་ལམ་སྒྲུབ...
    - text: ཐམས་ཅད་དུ་འགྲོ་བའི་ལམ་སྒྲུབ་པའི་རྒྱུ་ནི་ལས་མངོན་པར་འདུ་བྱེད་པའོ། །
    - gloss: ‘The causes that create the paths that lead to all destinations lie in the formation of karma.
  - `pos 5278 / Toh 99-PLAIN-5278` སེམས་ཅན་གང་དག་ཇི་ཙམ་དུ་མ་འོ...
    - text: སེམས་ཅན་གང་དག་ཇི་ཙམ་དུ་མ་འོངས་པའི་དུས་ན་བདེ་བ་མྱོང་བར་འགྱུར་བ་དེ་དག་ཐམས་ཅད་ད་ལྟར་བྱུང་བའི་ཕྱོགས་དཀར་པོ་འཕེལ་བར་བྱས་པས་མ་འོངས་པའི་དུས་སུ་བདེ་བ་མྱོང་བར་འགྱུར་རོ། །
    - gloss: Whatever happiness sentient beings will experience in the future—it is all due to fostering positivity in the present that one experiences happiness in the future.
  - `pos 5279 / Toh 99-PLAIN-5279` སེམས་ཅན་གང་དག་ཇི་ཙམ་དུ་ད་ལྟ...
    - text: སེམས་ཅན་གང་དག་ཇི་ཙམ་དུ་ད་ལྟར་བྱུང་བའི་དུས་སུ་སྡུག་བསྔལ་མྱོང་བ་དེ་དག་ཐམས་ཅད་ད་ལྟར་བྱུང་བའི་ཉོན་མོངས་པ་མ་བཟློག་པ་ཡིན་ནོ། །
    - gloss: Whatever suffering sentient beings undergo in the present, it all occurs because they do nothing to counteract their present afflictions.
  - `pos 5280 / Toh 99-PLAIN-5280` སེམས་ཅན་གང་དག་ཇི་ཙམ་དུ་ད་ལྟ...
    - text: སེམས་ཅན་གང་དག་ཇི་ཙམ་དུ་ད་ལྟར་བྱུང་བའི་དུས་སུ་བདེ་བ་མྱོང་བ་དེ་དག་ཐམས་ཅད་ད་ལྟར་བྱུང་བའི་ཉོན་མོངས་པ་བཟློག་པ་ཡིན་ནོ། །
    - gloss: Whatever happiness sentient beings experience in the present, it all occurs because they counteract their present afflictions.

### 星系 12 · The Ratnaketu Dh / The Quintessence

- Core: **The Play in Full · section 001** Toh 95
- Unit type: `section-window`; cluster units: `255`; unit segments: `120`; centroid sim: `0.9929`
- Gloss coverage in sampled unit: `119/120`
- Samples:
  - `pos 1 / Toh 95-PLAIN-001` ༄༅། །རྒྱ་གར་སྐད་དུ། ཨཱརྱ་ལ་...
    - text: ༄༅། །རྒྱ་གར་སྐད་དུ། ཨཱརྱ་ལ་ལི་ཏ་བི་སྟཱ་ར་ནཱ་མ་མ་ཧཱ་ཡཱ་ན་སཱུ་ཏྲ། བོད་སྐད་དུ།
  - `pos 2 / Toh 95-PLAIN-002` འཕགས་པ་རྒྱ་ཆེར་རོལ་པ་ཞེས་བྱ...
    - text: འཕགས་པ་རྒྱ་ཆེར་རོལ་པ་ཞེས་བྱ་བ་ཐེག་པ་ཆེན་པོའི་མདོ།
    - gloss: The Noble Great Vehicle Sūtra The Play in Full
  - `pos 3 / Toh 95-PLAIN-003` །བམ་པོ་དང་པོ།
    - text: །བམ་པོ་དང་པོ།
    - gloss: Chapter 1
  - `pos 60 / Toh 95-PLAIN-060` །དབང་ཕྱུག་དབང་ཕྱུག་ཆེན་པོ་ཙ...
    - text: །དབང་ཕྱུག་དབང་ཕྱུག་ཆེན་པོ་ཙན་དན་དང་། །དགའ་བོ་རབ་ཏུ་སེམས་ཞི་མཆོད་བྱས་དང་། །ཤིན་ཏུ་དགའ་བོ་ཞི་བ་ལྷ་ཡི་བུ། །བྱེ་བ་ལྷ་མང་དེ་དང་དེ་དག་རྣམས།
    - gloss: “There were millions of gods, Including Maheśvara, Candana, Īśvara, Nanda, Praśāntacitta, Mahita, Sunanda, And a god called Śānta.
  - `pos 61 / Toh 95-PLAIN-061` །ང་ཡི་ཞབས་ལ་ཕྱག་འཚལ་བསྐོར་བ...
    - text: །ང་ཡི་ཞབས་ལ་ཕྱག་འཚལ་བསྐོར་བྱས་ཏེ།
    - gloss: “They prostrated at my feet, circumambulated me,
  - `pos 62 / Toh 95-PLAIN-062` །ང་ཡི་མདུན་དུ་འདིར་ནི་འཁོད་...
    - text: །ང་ཡི་མདུན་དུ་འདིར་ནི་འཁོད་པར་གྱུར།
    - gloss: And gathered here before me.
  - `pos 118 / Toh 95-PLAIN-118` ལྷ་བརྒྱ་སྟོང་གི་སྐར་མའི་ཚོག...
    - text: ལྷ་བརྒྱ་སྟོང་གི་སྐར་མའི་ཚོགས་ཀྱིས་ཤིན་ཏུ་བརྒྱན་པ། བསམ་གཏན་དང་། རྣམ་པར་ཐར་པ་དང་། ཡེ་ཤེས་ཀྱི་དཀྱིལ་འཁོར་ཅན། བྱང་ཆུབ་ཀྱི་ཡན་ལག་གི་བདེ་བས་ཟླ་བའི་འོད་ཟེར་དུ་གྱུར་པ། མི་དང་ལྷ་མཁས་པའི་མེ་ཏོག་ཀུ་མུ་ད་ཁ་འབྱེད་པ་སྐྱེས་བུ་ཆེན་པོ་ཟླ་བ།
    - gloss: Adorned by the constellations of one hundred thousand gods, the moonlight of the soothing branches of awakening radiated from this sphere of concentration, liberation, and wisdom, causing the lilies among humans and gods to bloom.
  - `pos 119 / Toh 95-PLAIN-119` འཁོར་གྱི་གླིང་བཞིར་སོང་བ། བ...
    - text: འཁོར་གྱི་གླིང་བཞིར་སོང་བ། བྱང་ཆུབ་ཀྱི་ཡན་ལག་བདུན་གྱི་རིན་པོ་ཆེ་དང་ལྡན་པ།
    - gloss: The Great Bodhisattva was followed by a fourfold retinue, like the moon by the four continents, and he was endowed with the jewels of the seven branches of awakening.
  - `pos 120 / Toh 95-PLAIN-120` སེམས་ཅན་ཐམས་ཅད་ལ་སེམས་མཉམ་པ...
    - text: སེམས་ཅན་ཐམས་ཅད་ལ་སེམས་མཉམ་པར་སྦྱོར་བ། བློ་དཔྱད་ཐོགས་པ་མེད་པ།
    - gloss: He engaged all beings equally and possessed an unimpeded analytical capacity.

### 星系 11 · The Perfection o / The Perfection o

- Core: **The Perfection of Wisdom in Eighteen Thousand Lines · section 114** Toh 10
- Unit type: `section-window`; cluster units: `227`; unit segments: `120`; centroid sim: `0.9936`
- Gloss coverage in sampled unit: `120/120`
- Samples:
  - `pos 13561 / Toh 10-PLAIN-13561` །ཡང་དག་པར་སྤོང་བ་བཞི་སྒོམ་པ...
    - text: །ཡང་དག་པར་སྤོང་བ་བཞི་སྒོམ་པར་བྱེད་དོ། །རྫུ་འཕྲུལ་གྱི་རྐང་པ་བཞི་སྒོམ་པར་བྱེད་དོ། །དབང་པོ་ལྔ་དང་། སྟོབས་ལྔ་དང་། བྱང་ཆུབ་ཀྱི་ཡན་ལག་བདུན་དང་། འཕགས་པའི་ལམ་ཡན་ལག་བརྒྱད་པ་དག་སྒོམ་པར་བྱེད་དོ།
    - gloss: and to meditate on the four right efforts, to meditate on the four legs of miraculous power, and to meditate on the five faculties, five powers, seven limbs of awakening, and eightfold noble path.
  - `pos 13562 / Toh 10-PLAIN-13562` །ལམ་དེས་ཡོངས་སུ་ཟིན་པར་གྱུར...
    - text: །ལམ་དེས་ཡོངས་སུ་ཟིན་པར་གྱུར་པ་ནི། འཁོར་བ་ཇི་སྙེད་པ་ལས་ཡོངས་སུ་ཐར་བར་འགྱུར་ཏེ།
    - gloss: Assisted by that path, they are freed from saṃsāra in its entirety.
  - `pos 13563 / Toh 10-PLAIN-13563` རབ་འབྱོར་དེ་ལྟར་བྱང་ཆུབ་སེམ...
    - text: རབ་འབྱོར་དེ་ལྟར་བྱང་ཆུབ་སེམས་དཔའ་སེམས་དཔའ་ཆེན་པོ་འཕགས་པ་ཟག་པ་མེད་པའི་ཆོས་རྣམས་ཀྱིས་སེམས་ཅན་རྣམས་ཡོངས་སུ་འཛིན་པར་བྱེད་པ་ཡིན་ནོ།
    - gloss: It is thus, Subhūti, with the noble dharmas without outflows, that bodhisattva great beings look after beings.
  - `pos 13620 / Toh 10-PLAIN-13620` གཉིས་གང་ཞེ་ན།
    - text: གཉིས་གང་ཞེ་ན།
    - gloss: And what are the two?
  - `pos 13621 / Toh 10-PLAIN-13621` འབྲས་བུ་དེ་དག་ལ་གང་ལ་གནས་པར...
    - text: འབྲས་བུ་དེ་དག་ལ་གང་ལ་གནས་པར་འགྱུར་བ་དང་། གང་གིས་གནས་པར་འགྱུར་བ་དང་། གང་གནས་པར་འགྱུར་བའི་ངོ་བོ་ཉིད་མེད་པ་དང་། བླ་ན་མེད་པ་ཡང་དག་པར་རྫོགས་པའི་བྱང་ཆུབ་མངོན་པར་རྫོགས་པར་སངས་རྒྱས་ཀྱི་བར་དུ་དེ་ཙམ་གྱིས་ཆོག་པར་མི་འཛིན་པར་བདག་གིས་རྒྱུན་དུ་ཞུགས་པའི་འབྲས་བུ་ཐོབ་པར་མི་བྱ་བ་མ་ཡིན་ཏེ།
    - gloss: It is because those results where they might be located have no intrinsic nature, nor does that on account of which they might be located, nor those who might be located. And second, because up until they fully awaken to unsurpassed, perfect, complete awakening they are not easily satisfied.
  - `pos 13622 / Toh 10-PLAIN-13622` བདག་གིས་རྒྱུན་དུ་ཞུགས་པའི་འ...
    - text: བདག་གིས་རྒྱུན་དུ་ཞུགས་པའི་འབྲས་བུ་ཐོབ་ནས་ཀྱང་དེ་ལ་གནས་པར་མི་བྱའོ།
    - gloss: They think, ‘It is not that I should not reach the result of stream enterer, but even after having reached the result of stream enterer I should not stand there;
  - `pos 13678 / Toh 10-PLAIN-13678` དེ་འདི་ལྟར་དགེ་བའི་རྩ་བ་འདི...
    - text: དེ་འདི་ལྟར་དགེ་བའི་རྩ་བ་འདིས་བདག་བླ་ན་མེད་པ་ཡང་དག་པར་རྫོགས་པའི་བྱང་ཆུབ་མངོན་པར་རྫོགས་པར་སངས་རྒྱས་པའི་སངས་རྒྱས་ཀྱི་ཞིང་དེའི་སེམས་ཅན་རྣམས་ལྷའི་རེག་པ་ཕུན་སུམ་ཚོགས་པ་དང་ལྡན་པར་གྱུར་ཅིག་ཅེས་ཡོངས་སུ་སྔོ་བར་བྱེད་དོ།
    - gloss: ‘Through this wholesome root, may the beings in my buddhafield when I have fully awakened to unsurpassed, perfect, complete awakening experience perfect feelings of divine touch.’
  - `pos 13679 / Toh 10-PLAIN-13679` །རབ་འབྱོར་གཞན་ཡང་བྱང་ཆུབ་སེ...
    - text: །རབ་འབྱོར་གཞན་ཡང་བྱང་ཆུབ་སེམས་དཔའ་སེམས་དཔའ་ཆེན་པོ་འདི་སྙམ་དུ་སེམས་ཏེ། ཡིད་ལ་བསམས་པ་ཙམ་ཉིད་ཀྱིས་སངས་རྒྱས་རྣམས་དང་། སངས་རྒྱས་ཀྱི་ཉན་ཐོས་རྣམས་དང་། སེམས་ཅན་ཐམས་ཅད་ལ་འདོད་པའི་ཡོན་ཏན་ལྔ་པོ་གཟུགས་དང་སྒྲ་དང་། དྲི་དང་། རོ་དང་། རེག་བྱ་ཡིད་དུ་འོང་བ་དག་འབུལ་བར་གྱུར་ཅིག །སྙམ་དུ་སེམས་ཤིང་དེ་དག་ཕུལ་ནས་ཀྱང་།
    - gloss: “Furthermore, Subhūti, it occurs to bodhisattva great beings to think, ‘Just by thinking about it may I give the five sorts of sense objects—forms, sounds, smells, tastes, and feelings—pleasing to the mind to the buddhas, the buddhas’ śrāvakas, and all beings.’ Having thought that and given them, they dedicate it thus:
  - `pos 13680 / Toh 10-PLAIN-13680` དེ་འདི་ལྟར་དགེ་བའི་རྩ་བ་འདི...
    - text: དེ་འདི་ལྟར་དགེ་བའི་རྩ་བ་འདིས་བདག་བླ་ན་མེད་པ་ཡང་དག་པར་རྫོགས་པའི་བྱང་ཆུབ་མངོན་པར་རྫོགས་པར་སངས་རྒྱས་པའི་སངས་རྒྱས་ཀྱི་ཞིང་དེའི་ཉན་ཐོས་ཀྱི་དགེ་འདུན་ཐམས་ཅད་དང་། སེམས་ཅན་ཐམས་ཅད་ཀྱིས་ཡིད་ལ་བསམས་པ་ཙམ་གྱིས་འདོད་པའི་ཡོན་ཏན་ལྔ་པོ་གཟུགས་དང་། སྒྲ་དང་། དྲི་དང་། རོ་དང་། རེག་བྱ་ཡིད་དུ་འོང་བ་དག་འབྱུང་བར་གྱུར་ཅིག་ཅེས་ཡོངས་སུ་སྔོ་བར་བྱེད་དོ།
    - gloss: ‘Through this wholesome root, may all the śrāvaka saṅghas and all beings in my buddhafield when I have fully awakened to unsurpassed, perfect, complete awakening come to have the five sorts of sense objects—forms, sounds, smells, tastes, and feelings—pleasing to the mind just by thinking about it.’

### 星系 03 · The King of Samā / The Play in Full

- Core: **The King of Samādhis Sūtra · section 058** Toh 127
- Unit type: `section-window`; cluster units: `219`; unit segments: `120`; centroid sim: `0.994`
- Gloss coverage in sampled unit: `120/120`
- Samples:
  - `pos 6841 / Toh 127-PLAIN-6841` །རབ་ཏུ་བཀོད་ཅིང་ཡོངས་སུ་མྱ་...
    - text: །རབ་ཏུ་བཀོད་ཅིང་ཡོངས་སུ་མྱ་ངན་ལས་འདས་ནས་སེམས་ཅན་གྲངས་མེད་དཔག་ཏུ་མེད་པ་རྣམས་ཟག་པ་ཟད་པ་དགྲ་བཅོམ་པ་ཉིད་ལ་བཀོད་དོ།
    - gloss: He established countless, innumerable beings in the state of arhathood without outflows, and having done so passed into nirvāṇa.
  - `pos 6842 / Toh 127-PLAIN-6842` །རབ་ཏུ་བཀོད་ཅིང་ཡོངས་སུ་མྱ་...
    - text: །རབ་ཏུ་བཀོད་ཅིང་ཡོངས་སུ་མྱ་ངན་ལས་འདས་ན་སེམས་ཅན་གྲངས་མེད་དཔག་ཏུ་མེད་པ་དག་བླ་ན་མེད་པ་ཡང་དག་པར་རྫོགས་པའི་བྱང་ཆུབ་ལས་ཕྱིར་མི་ལྡོག་པ་ལ་བཀོད་དེ་ཡོངས་སུ་མྱ་ངན་ལས་འདས་པར་གྱུར་ཏོ།
    - gloss: He established countless, innumerable beings in irreversible progress toward the highest, complete enlightenment and then he passed into nirvāṇa.
  - `pos 6843 / Toh 127-PLAIN-6843` །ཀུན་དགའ་བོ་དེའི་ཚེ་བཅོམ་ལྡ...
    - text: །ཀུན་དགའ་བོ་དེའི་ཚེ་བཅོམ་ལྡན་འདས་རིན་པོ་ཆེའི་པད་མའི་ཟླ་བ་རྣམ་པར་དག་པ་མངོན་པར་འཕགས་པའི་རྒྱལ་པོ་དེ་བཞིན་གཤེགས་པ་དགྲ་བཅོམ་པ་ཡང་དག་པར་རྫོགས་པའི་སངས་རྒྱས་དེ་ཡོངས་སུ་མྱ་ངན་ལས་འདས་ནས་ལྔ་བརྒྱ་པ་ཐ་མ་ལ་དམ་པའི་ཆོས་ནུབ་པར་འགྱུར་བའི་དུས་ཀྱི་ཚེ་དམ་པའི་ཆོས་རབ་ཏུ་འཇིག་པར་འགྱུར་བ་ན། ཀུན་དགའ་བོ་རྒྱལ་པོ་དཔའ་བས་བྱིན་ཞེས་བྱ་བ་ཞིག་བྱུང་སྟེ།
    - gloss: “Ānanda, at that time, after the Bhagavān, the tathāgata, the arhat, the perfectly enlightened Buddha Ratna­padma­candra­viśuddhābhyud­gata­rāja had passed into nirvāṇa, during the last five hundred years when the supreme Dharma was vanishing, at the time when the supreme Dharma was being destroyed, there was, Ānanda, a king named Śūradatta.
  - `pos 6900 / Toh 127-PLAIN-6900` །གང་གིས་ཚུལ་ཁྲིམས་དྲི་མ་མེད།
    - text: །གང་གིས་ཚུལ་ཁྲིམས་དྲི་མ་མེད།
    - gloss: Those who keep their conduct stainless
  - `pos 6901 / Toh 127-PLAIN-6901` །སངས་རྒྱས་བསྔགས་པ་བསྲུངས་པ་ནི།
    - text: །སངས་རྒྱས་བསྔགས་པ་བསྲུངས་པ་ནི།
    - gloss: Are praised by the buddhas. {6} “ ‘Those who have honored
  - `pos 6902 / Toh 127-PLAIN-6902` །དེ་ཡིས་ཇི་སྙེད་སྔོན་བྱུང་བ...
    - text: །དེ་ཡིས་ཇི་སྙེད་སྔོན་བྱུང་བ། །བདེ་གཤེགས་ཐམས་ཅད་རི་མོར་བྱས།
    - gloss: The buddhas in the past
  - `pos 6958 / Toh 127-PLAIN-6958` །དེ་དེའི་ནུབ་མོ་འདས་པ་དང་རྒ...
    - text: །དེ་དེའི་ནུབ་མོ་འདས་པ་དང་རྒྱལ་པོའི་ཕོ་བྲང་འཁོར་རིན་ཆེན་ལྡན་དུ་ཞུགས་པར་གྱུར་ཏེ།
    - gloss: “When that night had passed he went into the capital city of Ratnāvatī.
  - `pos 6959 / Toh 127-PLAIN-6959` ཞུགས་ནས་སྲོག་ཆགས་བྱེ་བ་ཁྲག་...
    - text: ཞུགས་ནས་སྲོག་ཆགས་བྱེ་བ་ཁྲག་ཁྲིག་ཕྲག་སུམ་ཅུ་རྩ་དྲུག་སངས་རྒྱས་ཀྱི་ཆོས་ལས་ཕྱིར་མི་ལྡོག་པར་བཀོད་ཀྱང་ད་དུང་ཟས་ཀྱི་བྱ་བ་མ་བྱས་སོ།
    - gloss: After entering inside he established three hundred and sixty million beings irreversibly in the Dharma.
  - `pos 6960 / Toh 127-PLAIN-6960` །དེ་ཟས་གཅད་པ་བཅད་ནས་རྒྱལ་པོ...
    - text: །དེ་ཟས་གཅད་པ་བཅད་ནས་རྒྱལ་པོའི་ཕོ་བྲང་འཁོར་རིན་ཆེན་ལྡན་ནས་བྱུང་སྟེ། བཅོམ་ལྡན་འདས་ཀྱི་སེན་མོའི་མཆོད་རྟེན་གང་ན་ཡོད་པ་དེར་སོང་སྟེ།
    - gloss: However, he had not had his meal and therefore, fasting that day, he emerged from the capital city of Ratnāvatī and went to the stūpa that contained the fingernail of the Bhagavān;

### 星系 02 · The Hundred Deed

- Core: **The Hundred Deeds · section 019** Toh 340
- Unit type: `section-window`; cluster units: `214`; unit segments: `120`; centroid sim: `0.9934`
- Gloss coverage in sampled unit: `120/120`
- Samples:
  - `pos 2161 / Toh 340-PLAIN-2161` དེ་ནས་ཚངས་པས་བྱིན་གྱིས་བསམས...
    - text: དེ་ནས་ཚངས་པས་བྱིན་གྱིས་བསམས་པ་མི་འཐུན་པར་མ་བྱས་ཀྱི་བར་དུ་ནི། བདག་གིས་དེ་བསད་དུ་མི་རུང་གིས་ཕྱིར་ཡང་བདག་གིས་དེ་དང་མི་འཐུན་པར་བྱའོ་སྙམ་དུ་བསམས་ནས
    - gloss: “Brahmadatta thought, ‘Failing some dispute, I cannot kill him. Let me then fabricate some dispute with him.’
  - `pos 2162 / Toh 340-PLAIN-2162` རྒྱལ་པོ་ཚངས་པས་བྱིན་གྱིས་རྒ...
    - text: རྒྱལ་པོ་ཚངས་པས་བྱིན་གྱིས་རྒྱལ་པོ་དབང་ཆེན་སྡེ་དང་ཕྱིར་ཡང་མི་འཐུན་པར་བྱས་ནས།
    - gloss: So King Brahmadatta began a dispute with King Mahendrasena.
  - `pos 2163 / Toh 340-PLAIN-2163` དཔུང་གི་ཚོགས་ཡན་ལག་བཞི་གོ་བ...
    - text: དཔུང་གི་ཚོགས་ཡན་ལག་བཞི་གོ་བསྐོན་ཏེ། ཡུལ་པི་དེ་ཧར་སོང་ནས། གྲོང་ཁྱེར་དཔུང་གི་ཚོགས་ཡན་ལག་བཞིས་བསྐོར་ཏེ་འདུག་གོ། །
    - gloss: He armed the four divisions of his army and advanced on Videha, where they besieged the city,
  - `pos 2220 / Toh 340-PLAIN-2220` བཅོམ་ལྡན་འདས་ཀྱི་བསྟན་པ་ལ་ར...
    - text: བཅོམ་ལྡན་འདས་ཀྱི་བསྟན་པ་ལ་རབ་ཏུ་བྱུང་ནས། ཉོན་མོངས་པ་ཐམས་ཅད་སྤངས་ཏེ། དགྲ་བཅོམ་པ་ཉིད་མངོན་སུམ་དུ་བགྱིས་ནས།
    - gloss: that she went forth in the doctrine of the Blessed One, cast away all afflictive emotions, and manifested arhatship;
  - `pos 2221 / Toh 340-PLAIN-2221` བཅོམ་ལྡན་འདས་ཀྱིས་བརྩོན་འགྲ...
    - text: བཅོམ་ལྡན་འདས་ཀྱིས་བརྩོན་འགྲུས་བརྩམས་པ་རྣམས་ཀྱི་མཆོག་ཏུ་ཡང་བསྟན་ལགས།
    - gloss: and that the Blessed One also commended her for her superlative efforts?”
  - `pos 2222 / Toh 340-PLAIN-2222` བཅོམ་ལྡན་འདས་ཀྱིས་བཀའ་སྩལ་པ།
    - text: བཅོམ་ལྡན་འདས་ཀྱིས་བཀའ་སྩལ་པ།
    - gloss: The Blessed One replied,
  - `pos 2278 / Toh 340-PLAIN-2278` དེས་ཕ་མ་ལ་གསོལ་ནས་ཚེ་དང་ལྡན...
    - text: དེས་ཕ་མ་ལ་གསོལ་ནས་ཚེ་དང་ལྡན་པ་ཉེ་སྡེ་ཉིད་ཀྱི་ཐད་དུ་རབ་ཏུ་བྱུང་སྟེ་བསྙེན་པར་རྫོགས་སོ། །
    - gloss: He asked for his parents’ permission, went forth as a novice, and received full ordination in the presence of Venerable Upasena.
  - `pos 2279 / Toh 340-PLAIN-2279` དེ་ནས་དེ་ཕྱི་ཞིག་ན་དེ་མཁན་པ...
    - text: དེ་ནས་དེ་ཕྱི་ཞིག་ན་དེ་མཁན་པོ་ལ་མ་ཞུས་པར་དོན་ཞིག་ལ་རི་ཁྲོད་དེ་ནས་སོང་ནས།
    - gloss: One day he left his mountainside hermitage on an errand without notifying his preceptor.
  - `pos 2280 / Toh 340-PLAIN-2280` དེ་མཐར་གྱིས་ལྗོངས་རྒྱུ་ཞིང་...
    - text: དེ་མཐར་གྱིས་ལྗོངས་རྒྱུ་ཞིང་སོང་སོང་བ་ལས་ཡུལ་བཅོམ་བརླག་ཅེས་བྱ་བར་ཕྱིན་ཏེ། བཅོམ་བརླག་ན་བོང་བུའི་ཀུན་དགའ་ར་བ་ན་གནས་སོ། །
    - gloss: He made his way through the countryside and eventually arrived in Mathurā, where he stayed at Donkey Grove.

### 星系 07 · The King of Samā / Bouquet of Flowe

- Core: **Bouquet of Flowers · section 009** Toh 266
- Unit type: `section-window`; cluster units: `198`; unit segments: `82`; centroid sim: `0.9949`
- Gloss coverage in sampled unit: `82/82`
- Samples:
  - `pos 961 / Toh 266-PLAIN-961` །སྟེང་གི་ཕྱོགས་ན་འཇིག་རྟེན་...
    - text: །སྟེང་གི་ཕྱོགས་ན་འཇིག་རྟེན་གྱི་ཁམས་རིན་པོ་ཆེའི་རིགས་ཞེས་བྱ་བ་ན། དེ་བཞིན་གཤེགས་པ་རིན་པོ་ཆེ་ཐམས་ཅད་ཀྱིས་བརྒྱན་པའི་གཟུགས་འཛིན་པ་ཞེས་བྱ་བ་བཞུགས་སོ།
    - gloss: “Above, in the world system called Family of Jewels, dwells the thus-gone one called He Who Possesses a Body Adorned with All Jewels.
  - `pos 962 / Toh 266-PLAIN-962` །ཅིའི་ཕྱིར་འཇིག་རྟེན་གྱི་ཁམ...
    - text: །ཅིའི་ཕྱིར་འཇིག་རྟེན་གྱི་ཁམས་དེ་རིན་པོ་ཆེའི་རིགས་ཞེས་བྱ་ཞེ་ན།
    - gloss: Why is that world system called Family of Jewels?
  - `pos 963 / Toh 266-PLAIN-963` འོད་སྲུང་སངས་རྒྱས་ཀྱི་ཞིང་ད...
    - text: འོད་སྲུང་སངས་རྒྱས་ཀྱི་ཞིང་དེའི་སེམས་ཅན་རྣམས་བླ་ན་མེད་པ་ཡང་དག་པར་རྫོགས་པའི་བྱང་ཆུབ་ཏུ་ཡང་དག་པར་རབ་ཏུ་ཞུགས་ཏེ།
    - gloss: Kāśyapa, it is because the beings in that buddhafield have genuinely set out for unexcelled, perfect and complete awakening.
  - `pos 1001 / Toh 266-PLAIN-1001` །དེ་དག་དད་པར་ག་ལ་འགྱུར།
    - text: །དེ་དག་དད་པར་ག་ལ་འགྱུར།
    - gloss: Become filled with faith When hearing about unexcelled awakening? “Upon hearing about
  - `pos 1002 / Toh 266-PLAIN-1002` །ནོར་དང་མཛོད་རྣམས་མང་པོ་དག...
    - text: །ནོར་དང་མཛོད་རྣམས་མང་པོ་དག །ནོར་བུ་རིན་ཆེན་ཐོས་ནས་ནི།
    - gloss: The many kinds of gems and treasuries, One should truly seek them out,
  - `pos 1003 / Toh 266-PLAIN-1003` །ཤིན་ཏུ་བརྒྱན་པར་བྱའོ་ཞེས།...
    - text: །ཤིན་ཏུ་བརྒྱན་པར་བྱའོ་ཞེས། །དེ་དག་ཡང་དག་ཡང་ཚོལ་ལོ།
    - gloss: Hoping to adorn oneself well with them.
  - `pos 1040 / Toh 266-PLAIN-1040` །བྱང་ཆུབ་སེམས་དཔའ་སེམས་དཔའ་...
    - text: །བྱང་ཆུབ་སེམས་དཔའ་སེམས་དཔའ་ཆེན་པོ་དེ་དག་དང་། དགེ་སློང་དེ་དག་དང་། ལྷ་དང་། མི་དང་། ལྷ་མ་ཡིན་དང་། དྲི་ཟར་བཅས་པའི་འཇིག་རྟེན་ཡི་རངས་ཏེ། །བཅོམ་ལྡན་འདས་ཀྱིས་བཤད་པ་ལ་མངོན་པར་བསྟོད་དོ།
    - gloss: The bodhisattva-mahāsattvas, the monks, and the world with its gods, humans, asuras, and gandharvas rejoiced and praised what the Blessed One taught.
  - `pos 1041 / Toh 266-PLAIN-1041` །འཕགས་པ་མེ་ཏོག་གི་ཚོགས་ཞེས་...
    - text: །འཕགས་པ་མེ་ཏོག་གི་ཚོགས་ཞེས་བྱ་བ་ཐེག་པ་ཆེན་པོའི་མདོ་རྫོགས་སོ།།
    - gloss: This concludes the Noble Great Vehicle Sūtra “Bouquet of Flowers.”
  - `pos 1042 / Toh 266-PLAIN-1042` །།རྒྱ་གར་གྱི་མཁན་པོ་ཛྙཱ་ན་ས...
    - text: །།རྒྱ་གར་གྱི་མཁན་པོ་ཛྙཱ་ན་སིད་དྷི་དང་། ཞུ་ཆེན་གྱི་ལོ་ཙྪ་བ་བན་དེ་དྷརྨ་ཏཱ་ཤཱི་ལ་སོགས་པས་ཞུ་ཆེན་བགྱིས་ཏེ་གཏན་ལ་ཕབ་པ།།
    - gloss: This text was edited and finalized by the Indian preceptor Jñānasiddhi, the chief editor-translator Venerable Dharmatāśīla, and others.

### 星系 04 · The Chapter Teac / The Perfection o

- Core: **The Questions of Brahma­viśeṣacintin · section 015** Toh 160
- Unit type: `section-window`; cluster units: `181`; unit segments: `120`; centroid sim: `0.9898`
- Gloss coverage in sampled unit: `117/120`
- Samples:
  - `pos 1681 / Toh 160-PLAIN-1681` །ཇི་ནས་གཉིས་སུ་ཡང་མི་མཐོང་།...
    - text: །ཇི་ནས་གཉིས་སུ་ཡང་མི་མཐོང་། གཉིས་སུ་མེད་པར་ཡང་མི་མཐོང་བ་དེ་ལྟར་མཐོང་སྟེ།
    - gloss: Thus, to neither see them as dual or as nondual is the way they are seen.
  - `pos 1682 / Toh 160-PLAIN-1682` དེ་ལྟར་མཐོང་ན་མངོན་སུམ་དུ་ཡ...
    - text: དེ་ལྟར་མཐོང་ན་མངོན་སུམ་དུ་ཡེ་ཤེས་མཐོང་བ་ཡང་མི་མཐོང་སྟེ།
    - gloss: When seen in this way, even the seeing of the direct perception of wisdom is not seeing.
  - `pos 1683 / Toh 160-PLAIN-1683` གང་མི་མཐོང་བ་འདི་ནི་འཕགས་པ་...
    - text: གང་མི་མཐོང་བ་འདི་ནི་འཕགས་པ་མི་སྨྲ་བར་གྱུར་པའོ།
    - gloss: This not seeing anything is keeping the noble silence.
  - `pos 1740 / Toh 160-PLAIN-1740` རིགས་ཀྱི་བུ་ཡང་དེའི་ཚེ་སྟེང...
    - text: རིགས་ཀྱི་བུ་ཡང་དེའི་ཚེ་སྟེང་གི་ཕྱོགས་ནས་དེ་བཞིན་གཤེགས་པ་སྨན་པའི་རྒྱལ་པོའི་སངས་རྒྱས་ཀྱི་ཞིང་ནས་བྱང་ཆུབ་སེམས་དཔའ་བློ་གྲོས་མི་ཟད་པ་དང་། ཁྱད་པར་བློ་གྲོས་གཉིས་འོངས་ནས་དེ་གཉིས་བཅོམ་ལྡན་འདས་ཀུན་ཏུ་འོད་ཟེར་དེ་བཞིན་གཤེགས་པ་ག་ལ་བ་དེར་ཕྱིན་ཏེ།
    - gloss: Noble son, in the zenith direction, two bodhisattvas called Akṣayamati and Viśeṣamati left the buddha realm of the Thus-Gone One Bhaiṣajyarāja and went to meet the Thus-Gone One Samantaraśmi.
  - `pos 1741 / Toh 160-PLAIN-1741` བཅོམ་ལྡན་འདས་ཀྱི་ཞབས་ལ་མགོ་...
    - text: བཅོམ་ལྡན་འདས་ཀྱི་ཞབས་ལ་མགོ་བོས་ཕྱག་འཚལ་ནས་ལན་གསུམ་བསྐོར་ཏེ་ཕྱོགས་གཅིག་ཏུ་འདུག་གོ།
    - gloss: They prostrated to the Blessed One’s feet and circumambulated him three times. Then they took places by his side.
  - `pos 1742 / Toh 160-PLAIN-1742` །དེ་གཉིས་ལ་དེ་བཞིན་གཤེགས་པ་...
    - text: །དེ་གཉིས་ལ་དེ་བཞིན་གཤེགས་པ་དེས་སྣང་བ་ཡོངས་སུ་དག་པ་ཞེས་བྱ་བའི་ཏིང་ངེ་འཛིན་རྒྱ་ཆེར་ཡང་དག་པར་རབ་ཏུ་སྟོན་ཏོ།
    - gloss: At that point, the Thus-Gone One taught them, extensively and perfectly, the absorption called pure light in the following way:
  - `pos 1798 / Toh 160-PLAIN-1798` སྨྲས་པ། གང་ཆོས་གང་ལ་ཡང་རྣམ་...
    - text: སྨྲས་པ། གང་ཆོས་གང་ལ་ཡང་རྣམ་པར་མི་རྟོག་ན་དེ་ལྟར་མངོན་པར་བརྩོན་པས་མངོན་པར་རྟོགས་པ་འཐོབ་པར་འགྱུར་རོ།
    - gloss: “Exerting oneself without conceptualizing any phenomenon leads to realization.”
  - `pos 1799 / Toh 160-PLAIN-1799` །སྨྲས་པ། ཇི་ལྟར་ན་མངོན་པར་ར...
    - text: །སྨྲས་པ། ཇི་ལྟར་ན་མངོན་པར་རྟོགས་པ་མངོན་པར་རྟོགས་པ་ཡིན།
    - gloss: “What is realization?”
  - `pos 1800 / Toh 160-PLAIN-1800` སྨྲས་པ། མཉམ་པ་ཉིད་གང་གིས་ཆོ...
    - text: སྨྲས་པ། མཉམ་པ་ཉིད་གང་གིས་ཆོས་ཐམས་ཅད་མཉམ་པར་མཐོང་བ་ནི་དེ་ལྟར་ན་མངོན་པར་རྟོགས་པ་མངོན་པར་རྟོགས་པ་ཡིན་ནོ།
    - gloss: “Realization is seeing the equality of all phenomena.”

### 星系 09 · The Application 

- Core: **The Application of Mindfulness of the Sacred Dharma · section 151** Toh 287
- Unit type: `section-window`; cluster units: `156`; unit segments: `120`; centroid sim: `0.9956`
- Gloss coverage in sampled unit: `120/120`
- Samples:
  - `pos 18001 / Toh 287-PLAIN-18001` །དེ་ལྟ་བུའི་ཡོན་ཏན་དང་ལྡན་པ...
    - text: །དེ་ལྟ་བུའི་ཡོན་ཏན་དང་ལྡན་པའི་སར་སྐྱེ་བ་ནི་དགེ་བའི་ལས་རྣམ་པ་དུ་མ་རྣམས་ཀྱིས་ཡིན་ནོ།
    - gloss: Being born in a place that has such qualities is the effect of numerous virtuous actions.
  - `pos 18002 / Toh 287-PLAIN-18002` །དེས་ན་དེར་སྐྱེ་བའི་ལྷ་དེ་ད...
    - text: །དེས་ན་དེར་སྐྱེ་བའི་ལྷ་དེ་དག་རྣམས་ནི་དང་པོ་ཁོ་ན་རྒྱུན་གྱི་རི་ལ་སྐྱེ་བར་འགྱུར་རོ། །བག་མེད་པས་གནས་པར་ཡང་མི་འགྱུར་ཏེ། བདག་ཉིད་ལོག་པར་ལྟུང་བས་སོ།
    - gloss: “Thus, while the gods initially take birth in these mountains, they will not live carelessly, for they would then fall into the lower realms.
  - `pos 18003 / Toh 287-PLAIN-18003` །དེ་གསར་དུ་སྐྱེས་པར་གྱུར་པ་...
    - text: །དེ་གསར་དུ་སྐྱེས་པར་གྱུར་པ་ན་ནགས་དང་རྫིང་བུ་དང་སྤྲོ་བའི་པད་མའི་ནགས་ལ་རྣམ་པ་སྣ་ཚོགས་པར་མཆོག་ཏུ་དགའ་བའི་འདོད་པའི་ཡོན་ཏན་ལྔ་ཕུན་སུམ་ཚོགས་པས་རྔ་སྒྲ་དང་། ལྷའི་བུ་མོའི་ཚོགས་ཀྱིས་ཡོངས་སུ་བསྐོར་ནས་དགའ་ཞིང་ཀུན་ཏུ་སྤྱོད་པར་བྱེད་དེ།
    - gloss: Once born there, they begin to enjoy the numerous perfect sense pleasures that are available to them amid the forests, pools, and blooming lotus groves. To the sounds of music and surrounded by hosts of goddesses, they enjoy themselves and celebrate.
  - `pos 18060 / Toh 287-PLAIN-18060` །བརྟན་པས་ལེགས་པར་འཆིང་བ་ཡིན།
    - text: །བརྟན་པས་ལེགས་པར་འཆིང་བ་ཡིན།
    - gloss: It produces tight bonds.
  - `pos 18061 / Toh 287-PLAIN-18061` །གཟུགས་ཀྱི་སྤྱི་ནི་མ་མཐོང་ན།
    - text: །གཟུགས་ཀྱི་སྤྱི་ནི་མ་མཐོང་ན།
    - gloss: Yet when no universality of form is seen
  - `pos 18062 / Toh 287-PLAIN-18062` །ཡོངས་སྨིན་ཇི་ལྟར་སོ་སོ་ཡིན།
    - text: །ཡོངས་སྨིན་ཇི་ལྟར་སོ་སོ་ཡིན།
    - gloss: How can ripening be individual?
  - `pos 18118 / Toh 287-PLAIN-18118` སྙིང་ལ་ཀུན་ནས་ལེགས་པར་ལྡན་པ...
    - text: སྙིང་ལ་ཀུན་ནས་ལེགས་པར་ལྡན་པ་གང་ཡང་དྲི་ཞིམ་པོ་ཕུན་སུམ་ཚོགས་པ་རྣམས་འཐུང་བར་བྱེད་དེ།
    - gloss: What they drink is perfectly agreeable and endowed with the most exquisite aromas.
  - `pos 18119 / Toh 287-PLAIN-18119` རྣམ་པ་དེ་ལྟ་བུའི་དགའ་བ་སྐྱེ...
    - text: རྣམ་པ་དེ་ལྟ་བུའི་དགའ་བ་སྐྱེ་བར་འགྱུར་བ་དེ་ནི་གང་བརྗོད་པར་ཡང་མི་ནུས་སོ།
    - gloss: The joy that they feel is therefore indescribable.
  - `pos 18120 / Toh 287-PLAIN-18120` །དེ་ལྟར་རྒྱགས་པས་རྣམ་པར་རྒྱ...
    - text: །དེ་ལྟར་རྒྱགས་པས་རྣམ་པར་རྒྱུ་བའི་ལྷ་དེ་དག་རྣམས་རྩི་འཐུང་བར་བྱེད་ལ་ལྷན་ཅིག་སྤྱོད་པ་དང་བཅས་པ་རྣམས་དུས་ཡུན་རིང་དུ་རྗེས་སུ་འཇུག་གོ།
    - gloss: Traipsing around joyfully, they drink nectars and enjoy each other’s company for a long time.

### 星系 08 · The Good Eon

- Core: **The Good Eon · section 093** Toh 94
- Unit type: `section-window`; cluster units: `108`; unit segments: `120`; centroid sim: `0.9969`
- Gloss coverage in sampled unit: `120/120`
- Samples:
  - `pos 11041 / Toh 94-PLAIN-11041` དེ་བཞིན་གཤེགས་པ་རྒྱ་ཆེན་སྙི...
    - text: དེ་བཞིན་གཤེགས་པ་རྒྱ་ཆེན་སྙིང་པོ་ཡི། །སྐྱེ་བའི་ཡུལ་ནི་མཆོད་པ་མཐའ་ཡས་ཡིན། །
    - gloss: “The thus-gone Udāragarbha Will be born in a place called Infinite Worship.
  - `pos 11042 / Toh 94-PLAIN-11042` རིགས་ནི་བྲམ་ཟེ་ཡིན་ཏེ་འོད་ད...
    - text: རིགས་ནི་བྲམ་ཟེ་ཡིན་ཏེ་འོད་དཔག་ཚད། །ཉི་ཤུ་རྩ་གཉིས་ཡབ་ནི་ལེགས་རྟོགས་ཡིན། །ཐར་འདོད་མ་ཞེས་བྱ་བ་རྒྱལ་བའི་ཡུམ། །
    - gloss: His family will be brahmin, And his light will extend twenty-two leagues. “Excellent Realization will be his father, and Wish for Liberation will be this victor’s mother.
  - `pos 11043 / Toh 94-PLAIN-11043` སྲས་པོ་ལེགས་གྲོལ་རྣམ་གྲོལ་ར...
    - text: སྲས་པོ་ལེགས་གྲོལ་རྣམ་གྲོལ་རིམ་གྲོ་པ། །
    - gloss: Excellent Liberation will be his son and Liberation his attendant.
  - `pos 11100 / Toh 94-PLAIN-11100` མཆོད་རྟེན་ཡང་གཅིག་ཏུ་ཟད་དོ། །
    - text: མཆོད་རྟེན་ཡང་གཅིག་ཏུ་ཟད་དོ། །
    - gloss: There will also only be one stūpa.
  - `pos 11101 / Toh 94-PLAIN-11101` དེ་བཞིན་གཤེགས་པ་ལྷ་མཆོག་སྐྱ...
    - text: དེ་བཞིན་གཤེགས་པ་ལྷ་མཆོག་སྐྱེ་བའི་ཡུལ་ནི་ཡན་ལག་མཆོག་ཅེས་བྱའོ། །
    - gloss: “The thus-gone Uttamadeva will be born in a place called Supreme Limbs.
  - `pos 11102 / Toh 94-PLAIN-11102` རིགས་ནི་རྒྱལ་རིགས་སོ། །
    - text: རིགས་ནི་རྒྱལ་རིགས་སོ། །
    - gloss: His family will be kṣatriya.
  - `pos 11158 / Toh 94-PLAIN-11158` ཡབ་ནི་རྙོག་པ་མེད་པའི་འོད་ཅེ...
    - text: ཡབ་ནི་རྙོག་པ་མེད་པའི་འོད་ཅེས་བྱའོ། །
    - gloss: Immaculate Light will be his father.
  - `pos 11159 / Toh 94-PLAIN-11159` ཡུམ་ནི་དབྱིག་འགྲོ་མ་ཞེས་བྱའ...
    - text: ཡུམ་ནི་དབྱིག་འགྲོ་མ་ཞེས་བྱའོ། །
    - gloss: Jewel Movement will be his mother.
  - `pos 11160 / Toh 94-PLAIN-11160` སྲས་ནི་བློ་གྲོས་གསལ་བ་ཞེས་བ...
    - text: སྲས་ནི་བློ་གྲོས་གསལ་བ་ཞེས་བྱའོ། །
    - gloss: Clear Intelligence will be his son.

### 星系 10 · The Transcendent / Upholding the Ro

- Core: **The Transcendent Perfection of Wisdom in Ten Thousand Lines · section 053** Toh 11
- Unit type: `section-window`; cluster units: `44`; unit segments: `120`; centroid sim: `0.9851`
- Gloss coverage in sampled unit: `120/120`
- Samples:
  - `pos 6241 / Toh 11-PLAIN-6241` མངོན་པར་གཏོར། མངོན་པར་རབ་ཏུ...
    - text: མངོན་པར་གཏོར། མངོན་པར་རབ་ཏུ་གཏོར་ནས། ཚིག་འདི་སྐད་ཅེས་གནས་བརྟན་རབ་འབྱོར་འདི་དེ་བཞིན་གཤེགས་པའི་དེ་བཞིན་ཉིད་ཀྱི་དེ་བཞིན་གཤེགས་པའི་རྗེས་སུ་སྐྱེས་པ་ནི་ངོ་མཚར་ལགས་སོ་ཞེས་སྨྲས་སོ། །དེ་ནས་ཚེ་དང་ལྡན་པ་རབ་འབྱོར་གྱིས་གཏམ་དེ་ཉིད་ཀྱི་རྒྱུད་ནས་བཟུང་སྟེ། ལྷ་དེ་དག་ལ་འདི་སྐད་ཅེས་སྨྲས་སོ། །
    - gloss: Then the venerable Su­bhūti, picking up the thread of this conversation, addressed the gods as follows: “O gods!
  - `pos 6242 / Toh 11-PLAIN-6242` ལྷ་དག་དེ་ལྟར་ན་གནས་བརྟན་རབ་...
    - text: ལྷ་དག་དེ་ལྟར་ན་གནས་བརྟན་རབ་འབྱོར་ནི་གཟུགས་ཀྱི་རྗེས་སུ་མ་སྐྱེས།
    - gloss: The Elder Su­bhūti does not emulate physical forms.
  - `pos 6243 / Toh 11-PLAIN-6243` གཟུགས་ཀྱི་དེ་བཞིན་ཉིད་ཀྱི་ར...
    - text: གཟུགས་ཀྱི་དེ་བཞིན་ཉིད་ཀྱི་རྗེས་སུ་མ་སྐྱེས།
    - gloss: He does not emulate the real nature of physical forms.
  - `pos 6300 / Toh 11-PLAIN-6300` ཤ་ར་དྭ་ཏིའི་བུ་འདི་ཇི་སྙམ་ད...
    - text: ཤ་ར་དྭ་ཏིའི་བུ་འདི་ཇི་སྙམ་དུ་སེམས། ཅི་བྱ་འདབ་མ་མེད་པ་དེས་སླར་བདག་ཉིད་སུམ་ཅུ་རྩ་གསུམ་གྱི་ལྷ་རྣམས་ཀྱི་ནང་དུ་གཞག་པར་ནུས་སྙམ་འམ།
    - gloss: do you think, Śāradvatī­putra, that this wingless bird would be able to resettle among the gods of the Trāyastriṃśa realm?”
  - `pos 6301 / Toh 11-PLAIN-6301` གསོལ་པ། བཙུན་པ་བཅོམ་ལྡན་འདས...
    - text: གསོལ་པ། བཙུན་པ་བཅོམ་ལྡན་འདས་མ་ལགས་སོ། །
    - gloss: “No, Reverend Lord!”
  - `pos 6302 / Toh 11-PLAIN-6302` བཅོམ་ལྡན་འདས་ཀྱིས་བཀའ་སྩལ་པ...
    - text: བཅོམ་ལྡན་འདས་ཀྱིས་བཀའ་སྩལ་པ། ཤ་ར་དྭ་ཏིའི་བུ་ཡང་གལ་ཏེ་བྱ་འདབ་མ་མེད་པ་དེ། དེ་ནས་ལྷུང་བཞིན་དུ་འདི་སྙམ་དུ་སེམས་ཏེ།
    - gloss: The Blessed One replied, “Again, Śāradvatī­putra, suppose this wingless bird while descending from there were to think, ‘O!
  - `pos 6358 / Toh 11-PLAIN-6358` བརྩོན་འགྲུས་རྩོམ་པ་དང་། བསམ...
    - text: བརྩོན་འགྲུས་རྩོམ་པ་དང་། བསམ་གཏན་དག་ལ་སྙོམས་པར་འཇུག་པ་དང་། ཤེས་རབ་སྒོམ་པ་དང་། དེ་བཞིན་དུ་སྦྱར་ཏེ། རྣམ་པ་ཐམས་ཅད་མཁྱེན་པ་ཉིད་ཀྱི་བར་ལ་སྤྱོད་པའི་ཆོས་དེ་དག་ཀྱང་མ་མཆིས་ཤིང་མི་དམིགས་པའི་སླད་དུ་སྟེ།
    - gloss: Reverend Lord!
  - `pos 6359 / Toh 11-PLAIN-6359` བཙུན་པ་བཅོམ་ལྡན་འདས་རྣམ་གྲང...
    - text: བཙུན་པ་བཅོམ་ལྡན་འདས་རྣམ་གྲངས་དེས་ན། བྱང་ཆུབ་སེམས་དཔའ་སེམས་དཔའ་ཆེན་པོའི་བླ་ན་མེད་པ་ཡང་དག་པར་རྫོགས་པའི་བྱང་ཆུབ་ནི་འབྱུང་སླ་བ་དང་། མངོན་པར་རྫོགས་པར་སངས་རྒྱས་པར་སླ་ལགས་སོ། །
    - gloss: For these reasons, the unsurpassed, genuinely perfect enlightenment of great bodhisattva beings is easy to bring forth, and it is easy to attain manifestly perfect buddhahood!
  - `pos 6360 / Toh 11-PLAIN-6360` དེ་ཅིའི་སླད་དུ་ཞེ་ན། བཙུན་པ...
    - text: དེ་ཅིའི་སླད་དུ་ཞེ་ན། བཙུན་པ་བཅོམ་ལྡན་འདས་འདི་ལྟར་གཟུགས་ནི་ངོ་བོ་ཉིད་ཀྱིས་སྟོང་།
    - gloss: If one were to ask why, Reverend Lord, it is because physical forms are empty of their own essential nature.
