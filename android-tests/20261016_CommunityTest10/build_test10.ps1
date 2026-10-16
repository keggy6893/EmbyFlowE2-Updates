$ErrorActionPreference = 'Stop'
$project = 'C:\Users\bumse\AndroidStudioProjects\EmbyFlowAndroid'
$destination = 'C:\Users\bumse\Downloads\TCL'
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$stage = Join-Path $destination "EmbyFlowAndroid_CommunityTest_$stamp"
$utf8 = New-Object System.Text.UTF8Encoding($false)
$expected = @{
 'app\src\main\java\de\embyflow\androidtv\EmbyPlayerActivity.kt' = '17561480eba25de8b2cba288a855dca1a7b7c78a7489108c542e90fb3f8f7a5c'
 'app\src\main\AndroidManifest.xml' = '0601c23939ebe72ee4566418077323732aef10c2816c0b8a4a642762b713ee41'
 'app\src\main\java\de\embyflow\androidtv\MainActivity.kt' = '19bdf46e8e94b0c15c4d489ce405284855861ea4fa1a1a603c38236a11d95ee2'
 'app\build.gradle.kts' = '08744b6fda00b118facb06b823c327206843a7a66bfcb2f2ee50d12a551c1d47'
 'app\src\main\res\xml\backup_rules.xml' = '6cf1a27e6807b1d24e41d3fbe7ddc1bfe1f42226027964f6eaf477d71b43b283'
 'app\src\main\res\xml\data_extraction_rules.xml' = 'cb1fc47ab4a984530ed60e0e6ee638929c3038290e7e7e0b4b03a3a30fbe7381'
}
foreach ($relative in $expected.Keys) {
 $file = Join-Path $project $relative
 if (!(Test-Path $file) -or (Get-FileHash $file -Algorithm SHA256).Hash -ne $expected[$relative]) {
  throw "Quellstand abweichend: $relative. Nichts geaendert."
 }
}
New-Item -ItemType Directory -Path $destination -Force | Out-Null
# Current source ZIP remains the pre-change checkpoint. Work on a separate copy.
robocopy $project $stage /E /XD .gradle build .git .idea /R:1 /W:1 /NFL /NDL /NJH /NJS | Out-Null
if ($LASTEXITCODE -ge 8) { throw 'Projektkopie fehlgeschlagen.' }
function Replace-Once([string]$Text, [string]$Before, [string]$After) {
 if (($Text.Split(@($Before), [StringSplitOptions]::None).Count - 1) -ne 1) {
  throw 'Einbaustelle nicht eindeutig. Originalprojekt unveraendert.'
 }
 return $Text.Replace($Before, $After)
}
$main = Join-Path $stage 'app\src\main\java\de\embyflow\androidtv\MainActivity.kt'
$text = [IO.File]::ReadAllText($main).Replace("`r`n", "`n")
$before = @'
            if (hasServer && hasToken && hasUser) {
                fetchMedia("Movie")
            }
'@
$after = @'
            if (hasServer && hasToken && hasUser) {
                fetchMedia("Movie")
            } else {
                openEmbySettings()
            }
'@
$text = Replace-Once $text $before $after
$before = @'
                            screen.invalidate()
                        }

                    } catch (e: Exception) {
'@
$after = @'
                            screen.invalidate()
                            fetchMedia("Movie")
                        }

                    } catch (e: Exception) {
'@
$text = Replace-Once $text $before $after
$before = @'
            rectangle(c, 1125f, 813f, 16f, 16f, Color.RED)
            text(c, "Zurück", 1150f, 827f, 16f)

            rectangle(c, 1242f, 813f, 16f, 16f, Color.GREEN)
            text(c, "Abspielen", 1265f, 827f, 16f)

            rectangle(c, 1357f, 813f, 16f, 16f, Color.YELLOW)
            text(c, "Ein-/Ausloggen", 1380f, 827f, 16f)
'@
$after = @'
            text(c, "Mit den Pfeiltasten auswählen", 1120f, 822f, 19f)
            text(c, "OK drücken zum Öffnen", 1120f, 849f, 19f)
            text(c, "Zurück drücken zum Beenden", 1120f, 876f, 19f)
'@
$text = Replace-Once $text $before $after
$text = Replace-Once $text 'text(c, "EmbyFlowE2", 249f, 56f, 28f)' 'text(c, "EmbyFlow Android", 249f, 56f, 28f)'
$text = $text.Replace('"Info / Einstellungen"', '"Einstellungen"')
$text = Replace-Once $text 'text(c, "Aktionen", 1120f, 792f, 21f, cyan)' 'text(c, "Fernbedienung", 1120f, 792f, 21f, cyan)'
$before = @'
    private var mediaMessage = "Mediathek noch nicht geladen"
'@
$after = @'
    private var mediaMessage = "Mediathek noch nicht geladen"
    private var libraryUpdateStatus = "Noch nicht aktualisiert"
'@
$text = Replace-Once $text $before $after
$before = @'
        val requestGeneration = ++mediaLoadGeneration
'@
$after = @'
        val requestGeneration = ++mediaLoadGeneration
        libraryUpdateStatus = "Mediathek wird aktualisiert …"
'@
$text = Replace-Once $text $before $after
$before = @'
                    favoriteVariants = variantsById
'@
$after = @'
                    libraryUpdateStatus = "Zuletzt aktualisiert: " +
                        java.text.SimpleDateFormat("HH:mm", java.util.Locale.GERMANY).format(java.util.Date()) + " Uhr"
                    favoriteVariants = variantsById
'@
$text = Replace-Once $text $before $after
$before = @'
                    mediaMessage = "Fehler: ${e.message}"
'@
$after = @'
                    libraryUpdateStatus = "Aktualisierung fehlgeschlagen"
                    mediaMessage = "Fehler: ${e.message}"
'@
$text = Replace-Once $text $before $after
$before = @'
            text(c, "Auswahl: ${mediaSelected + 1}", 695f, 847f, 16f)
'@
$after = @'
            text(c, "Auswahl: ${mediaSelected + 1}", 695f, 847f, 16f)
            text(c, libraryUpdateStatus, 695f, 876f, 19f)
'@
$text = Replace-Once $text $before $after
$before = @'
                        1 -> {
                            if (mediaEntries.isNotEmpty()) {
                                focusArea = 2
                            } else {
                                actionIndex = 1
                            }
                        }
'@
$after = @'
                        1 -> {
                            actionIndex = (actionIndex + 1).coerceAtMost(actions.lastIndex)
                        }
'@
$text = Replace-Once $text $before $after
$before = @'
                        1 -> {
                            focusArea = 0
                        }
'@
$after = @'
                        1 -> {
                            if (actionIndex > 0) actionIndex-- else focusArea = 0
                        }
'@
$text = Replace-Once $text $before $after
$before = @'
                        selected = (selected + 1).coerceAtMost(menu.lastIndex)
                    } else if (focusArea == 2) {
'@
$after = @'
                        selected = (selected + 1).coerceAtMost(menu.lastIndex)
                    } else if (focusArea == 1) {
                        if (mediaEntries.isNotEmpty()) focusArea = 2
                    } else if (focusArea == 2) {
'@
$text = Replace-Once $text $before $after
$before = @'
                        mediaSelected = (mediaSelected - 2).coerceAtLeast(0)
                    }
                }

                KeyEvent.KEYCODE_DPAD_RIGHT
'@
$after = @'
                        if (mediaSelected < 2) {
                            focusArea = 1
                        } else {
                            mediaSelected = (mediaSelected - 2).coerceAtLeast(0)
                        }
                    }
                }

                KeyEvent.KEYCODE_DPAD_RIGHT
'@
$text = Replace-Once $text $before $after
$before = @'
                        val currentMovie = currentSlides[currentIndex]
'@
$after = @'
                        val currentMovie = currentSlides[currentIndex]
                        displayedSlideshowItem = currentMovie
'@
$text = Replace-Once $text $before $after
$before = @'
        private val actions = listOf("Abspielen", "Details")
'@
$after = @'
        private val actions = listOf("Abspielen", "Details")
        private var displayedSlideshowItem: MediaEntry? = null
'@
$text = Replace-Once $text $before $after
$before = @'
                "Abspielen" -> playSelectedMedia()
'@
$after = @'
                "Details" -> {
                    val item = displayedSlideshowItem
                    if (item != null) {
                        startActivity(Intent(this@MainActivity, EmbyDetailsActivity::class.java).apply {
                            putExtra("item_id", item.id)
                            putExtra("item_type", item.type)
                            putExtra("item_title", item.title)
                        })
                    } else {
                        Toast.makeText(this@MainActivity, "Slideshow wird noch geladen.", Toast.LENGTH_SHORT).show()
                    }
                }

                "Abspielen" -> playSelectedMedia()
'@
$text = Replace-Once $text $before $after
$before = @'
    private fun fetchMedia(category: String, resume: Boolean = false, section: String = "", parentId: String = "") {
'@
$after = @'
    @Volatile private var dailyHomeExpiresAt = 0L
    private val dailyHomeTick = object : Runnable {
        override fun run() {
            if (isFinishing || isDestroyed) return
            if (dailyHomeExpiresAt > 0L && System.currentTimeMillis() >= dailyHomeExpiresAt &&
                !resumeGridActive && !categoryGridActive && hasWindowFocus()) {
                dailyHomeExpiresAt = 0L
                fetchMedia("Movie")
            }
            screen.postDelayed(this, 60000L)
        }
    }

    private fun dailyHomeItems(server: String, userId: String, token: String): List<MediaEntry> {
        val prefs = getSharedPreferences("embyflow", Context.MODE_PRIVATE)
        val scope = "$server|$userId"
        val now = System.currentTimeMillis()
        val savedAt = prefs.getLong("home_daily_at_v1", 0L)
        val sameAccount = prefs.getString("home_daily_scope_v1", "") == scope
        val saved = prefs.getString("home_daily_items_v1", "[]").orEmpty()
        val array: JSONArray
        if (sameAccount && savedAt > 0L && now >= savedAt && now - savedAt < 86400000L) {
            array = JSONArray(saved)
            dailyHomeExpiresAt = savedAt + 86400000L
        } else {
            val previous = if (sameAccount) JSONArray(saved) else JSONArray()
            val previousIds = (0 until previous.length()).map { previous.getJSONObject(it).optString("Id") }.toSet()
            val user = URLEncoder.encode(userId, "UTF-8")
            val connection = URL("$server/Users/$user/Items?Recursive=true&IncludeItemTypes=Movie,Series&SortBy=Random&Fields=Overview&Limit=40").openConnection() as HttpURLConnection
            connection.connectTimeout = 10000
            connection.readTimeout = 15000
            connection.setRequestProperty("X-Emby-Token", token)
            val response = try {
                if (connection.responseCode != 200) throw Exception("Tagesauswahl HTTP ${connection.responseCode}")
                connection.inputStream.bufferedReader().use { it.readText() }
            } finally { connection.disconnect() }
            val candidates = JSONObject(response).getJSONArray("Items")
            val all = (0 until candidates.length()).map { candidates.getJSONObject(it) }.distinctBy { it.optString("Id") }
            val fresh = all.filter { it.optString("Id") !in previousIds }
            val chosen = (fresh + all.filter { it.optString("Id") in previousIds }).take(4)
            array = JSONArray()
            chosen.forEach { array.put(it) }
            prefs.edit().putString("home_daily_scope_v1", scope)
                .putString("home_daily_items_v1", array.toString())
                .putLong("home_daily_at_v1", now).apply()
            dailyHomeExpiresAt = now + 86400000L
        }
        return (0 until array.length()).map { index ->
            val obj = array.getJSONObject(index)
            MediaEntry(obj.getString("Id"), obj.optString("Name", "Ohne Titel"),
                obj.optString("Type", "Movie"), obj.optString("Overview", ""))
        }
    }

    private fun fetchMedia(category: String, resume: Boolean = false, section: String = "", parentId: String = "") {
'@
$text = Replace-Once $text $before $after
$before = @'
        loadDailySlideshow()
        scheduleDailySlideRefresh()
'@
$after = @'
        loadDailySlideshow()
        scheduleDailySlideRefresh()
        screen.postDelayed(dailyHomeTick, 60000L)
'@
$text = Replace-Once $text $before $after
$before = @'
                runOnUiThread {
                    if (requestGeneration != mediaLoadGeneration || isFinishing || isDestroyed) return@runOnUiThread
                    libraryUpdateStatus = "Zuletzt aktualisiert: " +
'@
$after = @'
                val displayItems = if (!resume && section.isBlank() && parentId.isBlank()) {
                    loaded.take(2) + dailyHomeItems(server, userId, token)
                } else uniqueItems
                runOnUiThread {
                    if (requestGeneration != mediaLoadGeneration || isFinishing || isDestroyed) return@runOnUiThread
                    libraryUpdateStatus = "Zuletzt aktualisiert: " +
'@
$text = Replace-Once $text $before $after
$before = @'
                    mediaEntries = uniqueItems
'@
$after = @'
                    mediaEntries = displayItems
'@
$text = Replace-Once $text $before $after
$before = @'
                (if (resume || section == "Favoriten") uniqueItems else loaded).forEach { item ->
'@
$after = @'
                displayItems.forEach { item ->
'@
$text = Replace-Once $text $before $after
$text = Replace-Once $text 'import org.json.JSONObject' "import org.json.JSONObject`nimport org.json.JSONArray"
$before = @'
    private fun fetchMedia(category: String, resume: Boolean = false, section: String = "", parentId: String = "") {
'@
$after = @'
    private fun fetchMedia(category: String, resume: Boolean = false, section: String = "", parentId: String = "", searchTerm: String = "") {
'@
$text = Replace-Once $text $before $after
$before = @'
                    if (parentId.isNotBlank()) {
                        params.remove("Recursive=true")
'@
$after = @'
                    if (searchTerm.isNotBlank()) {
                        params.add("SearchTerm=" + URLEncoder.encode(searchTerm, "UTF-8"))
                    }
                    if (parentId.isNotBlank()) {
                        params.remove("Recursive=true")
'@
$text = Replace-Once $text $before $after
$before = @'
                    if (parentId.isBlank() && section.isNotBlank() && (section !in listOf("Filme", "Serien", "Favoriten", "Neu hinzugefügt") && !section.startsWith("Neu: "))
'@
$after = @'
                    if (searchTerm.isBlank() && parentId.isBlank() && section.isNotBlank() && (section !in listOf("Filme", "Serien", "Favoriten", "Neu hinzugefügt") && !section.startsWith("Neu: "))
'@
$text = Replace-Once $text $before $after
$before = @'
                            if (query.isNotBlank()) {
                                Toast.makeText(
                                    this@MainActivity,
                                    "Suche wird als Nächstes ergänzt.",
                                    Toast.LENGTH_SHORT
                                ).show()
                            }
'@
$after = @'
                            if (query.isNotBlank()) {
                                fetchMedia("Movie,Series", section = "Suche: $query", searchTerm = query)
                            }
'@
$text = Replace-Once $text $before $after
$before = @'
                    mediaMessage = if (resume) {
'@
$after = @'
                    mediaMessage = if (searchTerm.isNotBlank()) {
                        if (totalCount == 0) "Keine Treffer gefunden"
                        else "${uniqueItems.size} von $totalCount Treffern geladen"
                    } else if (resume) {
'@
$text = Replace-Once $text $before $after
$before = @'
                "Suche" -> {
                    val input = EditText(this@MainActivity).apply {
                        hint = "Titel eingeben"
                        setSingleLine(true)
                    }

                    AlertDialog.Builder(this@MainActivity)
                        .setTitle("EmbyFlow Suche")
                        .setView(input)
                        .setNegativeButton("Abbrechen", null)
                        .setPositiveButton("Suchen") { _, _ ->
                            val query = input.text.toString().trim()

                            if (query.isNotBlank()) {
                                fetchMedia("Movie,Series", section = "Suche: $query", searchTerm = query)
                            }
                        }
                        .show()
                }
'@
$after = @'
                "Suche" -> {
                    E2SearchKeyboard.show(this@MainActivity) { query ->
                        fetchMedia("Movie,Series", section = "Suche: $query", searchTerm = query)
                    }
                }
'@
$text = Replace-Once $text $before $after
$before = @'
            .setTitle("EmbyFlow - Serververbindung")
            .setView(layout)
'@
$after = @'
            .setTitle("EmbyFlow - Serververbindung")
            .setView(layout)
            .setNeutralButton("Wiedergabe") { _, _ ->
                val enabled = prefs.getBoolean("stable_playback_v1", false)
                AlertDialog.Builder(this)
                    .setTitle("Stabilitätsmodus")
                    .setMessage("Mehr Videopuffer gegen kurze Netzaussetzer. Der Start kann länger dauern. Gilt ab dem nächsten Filmstart.")
                    .setPositiveButton(if (enabled) "Ausschalten" else "Einschalten") { _, _ ->
                        prefs.edit().putBoolean("stable_playback_v1", !enabled).apply()
                        Toast.makeText(this, if (!enabled) "Stabilitätsmodus eingeschaltet" else "Stabilitätsmodus ausgeschaltet", Toast.LENGTH_LONG).show()
                    }
                    .setNegativeButton("Abbrechen", null).show()
            }
'@
$text = Replace-Once $text $before $after
[IO.File]::WriteAllText($main, $text, $utf8)
$keyboard = @'
package de.embyflow.androidtv

import android.app.Activity
import android.app.Dialog
import android.content.Intent
import android.graphics.*
import android.view.*
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import kotlin.concurrent.thread

internal object E2SearchKeyboard {
 fun show(activity: Activity, accept: (String) -> Unit) {
  val dialog=Dialog(activity); dialog.requestWindowFeature(Window.FEATURE_NO_TITLE)
  val view=object: View(activity) {
   val prefs=activity.getSharedPreferences("embyflow",Activity.MODE_PRIVATE)
   val navy=Color.rgb(12,24,39); val cyan=Color.rgb(56,199,244); val yellow=Color.rgb(229,200,75)
   val pen=Paint(Paint.ANTI_ALIAS_FLAG)
   val letters=("ABCDEFGHIJKLMNOPQRSTUVWXYZ".map { it.toString() }+listOf("Ä","Ö","Ü","ß","123","SPACE","DEL"))
   val numbers="0123456789".map { it.toString() }+listOf("ABC","SPACE","DEL")
   var historyTarget=0; var numeric=false; var key=0; var mode=0; var selected=0; var filter=0; var query="";var status="Ab 2 Buchstaben erscheinen automatisch Treffer mit Emby-Postern"
   var generation=0;var closed=false
   var results=listOf<JSONObject>();val posters=mutableMapOf<String,Bitmap>()
   val scope=prefs.getString("server","").orEmpty()+"|"+prefs.getString("userId","").orEmpty()
   val historyKey="search_history_v9_"+android.util.Base64.encodeToString(scope.toByteArray(),android.util.Base64.NO_WRAP)
   var history=readHistory()
   var pending:Runnable?=null
   fun readHistory():List<JSONObject> = try {val a=JSONArray(prefs.getString(historyKey,"[]"));(0 until a.length()).map {a.getJSONObject(it)}}catch(_:Exception){emptyList()}
   fun saveHistory() {
    val term=query.trim();if(term.length<2)return
    val entry=JSONObject().put("term",term).put("time",System.currentTimeMillis())
    history=(listOf(entry)+history.filterNot {it.optString("term").equals(term,true)}).take(20)
    persistHistory()
   }
   fun persistHistory(){val a=JSONArray();history.forEach {a.put(it)};prefs.edit().putString(historyKey,a.toString()).apply()}
   fun keys()=if(numeric)numbers else letters
   fun keyBoxes():List<RectF>{var x=480f;return keys().map {k->val w=when(k){"123","ABC","DEL"->58f;"SPACE"->68f;else->34f};RectF(x,264f,x+w,312f).also{x+=w+3f}}}
   fun label(c:Canvas,t:String,x:Float,y:Float,size:Float,color:Int=Color.WHITE,bold:Boolean=false){pen.style=Paint.Style.FILL;pen.color=color;pen.textSize=size;pen.typeface=if(bold)Typeface.DEFAULT_BOLD else Typeface.DEFAULT;c.drawText(t,x,y,pen)}
   fun frame(c:Canvas,r:RectF,color:Int=Color.rgb(38,59,74),radius:Float=12f){pen.style=Paint.Style.STROKE;pen.strokeWidth=2f;pen.color=color;c.drawRoundRect(r,radius,radius,pen)}
   fun short(t:String,width:Float,size:Float):String {pen.textSize=size;pen.typeface=Typeface.DEFAULT;return if(pen.measureText(t)<=width)t else t.take(pen.breakText(t,true,width-pen.measureText("…"),null))+"…"}
   override fun onDraw(c:Canvas){c.save();c.scale(width/1920f,height/1080f);c.drawColor(navy)
    label(c,"EmbyFlow",40f,58f,32f,Color.rgb(220,229,238));label(c,"Suche",40f,100f,27f,cyan,true)
    frame(c,RectF(38f,124f,428f,884f));frame(c,RectF(450f,124f,1878f,884f))
    label(c,"Letzte Suchen",62f,178f,27f,Color.WHITE,true)
    if(history.isEmpty())label(c,"Noch keine gespeicherten Suchen",62f,225f,19f,Color.LTGRAY)
    history.take(8).forEachIndexed {i,e->val y=224f+i*72f
     if(mode==1&&selected==i)frame(c,RectF(54f,y-27f,411f,y+35f),yellow,5f)
     label(c,short(e.optString("term"),320f,22f),66f,y,22f)
     label(c,java.text.SimpleDateFormat("dd.MM.yyyy HH:mm",java.util.Locale.GERMANY).format(java.util.Date(e.optLong("time"))),76f,y+25f,16f,Color.GRAY)
    }
    pen.style=Paint.Style.FILL;pen.color=Color.rgb(16,36,50);c.drawRoundRect(RectF(480f,150f,1848f,214f),11f,11f,pen)
    label(c,short(query.ifEmpty{"Suchbegriff"},1320f,32f),498f,194f,32f,Color.WHITE,true)
    label(c,"Ab 2 Buchstaben erscheinen automatisch Treffer mit Emby-Postern",492f,238f,18f,Color.rgb(131,148,163))
    keyBoxes().forEachIndexed {i,b->if(mode==0&&i==key)frame(c,RectF(b.left-4,b.top-4,b.right+4,b.bottom+4),yellow,7f)
     val k=keys()[i];val t=if(k=="SPACE")"_" else k;pen.textSize=18f;pen.typeface=Typeface.DEFAULT_BOLD;val tx=b.centerX()-pen.measureText(t)/2;label(c,t,tx,b.centerY()+6,18f,Color.rgb(220,229,238),true)
    }
    listOf("Alle","Filme","Serien").forEachIndexed {i,t->val x=480f+i*180f;if(mode==3&&selected==i)frame(c,RectF(x-5,325f,x+160,363f),yellow,5f);label(c,(if(filter==i)"● " else "  ")+t,x,354f,21f,cyan)}
    label(c,status,480f,398f,19f,Color.rgb(149,167,181))
    val start=if(mode==2)(selected/5)*5 else 0
    results.drop(start).take(5).forEachIndexed {i,obj->val x=480f+i*264f;val b=RectF(x,424f,x+214f,728f);val bitmap=posters[obj.optString("Id")]
     if(bitmap!=null){pen.style=Paint.Style.FILL;c.drawBitmap(bitmap,null,b,pen)}else{frame(c,b);label(c,"Lade Poster",x+20,580f,19f,Color.GRAY)}
     if(mode==2&&selected==start+i)frame(c,RectF(x-6,418f,x+220,734f),yellow,3f)
     label(c,short(obj.optString("Name"),214f,18f),x,766f,18f,Color.WHITE,true)
     label(c,(if(obj.optString("Type")=="Series")"Serie" else "Film")+" · "+obj.optString("ProductionYear",""),x,813f,16f,Color.GRAY)
    }
    label(c,"Pfeile: Auswahl   OK: Übernehmen / Öffnen   Zurück: Schließen",40f,944f,20f,Color.LTGRAY)
    label(c,"↓ Filter / Poster    ← Verlauf    DEL: Zeichen löschen",40f,980f,20f,Color.LTGRAY)
    if(mode==1){ if(selected==history.take(8).size)frame(c,RectF(54f,830f,411f,868f),yellow,5f);label(c,"Eintrag löschen",62f,856f,20f,cyan) }
    c.restore()
   }
   fun search(){generation++;val g=generation;pending?.let{removeCallbacks(it)};results=emptyList();selected=0
    if(query.trim().length<2){status="Mindestens 2 Zeichen eingeben";invalidate();return}
    status="Suche läuft …";invalidate()
    val term=query.trim();val type=listOf("Movie,Series","Movie","Series")[filter]
    val task=Runnable {thread {try{
     val server=prefs.getString("server","").orEmpty().trimEnd('/');val user=URLEncoder.encode(prefs.getString("userId","").orEmpty(),"UTF-8");val token=prefs.getString("token","").orEmpty()
     fun read(address:String):String{val cn=URL(address).openConnection() as HttpURLConnection;cn.connectTimeout=8000;cn.readTimeout=12000;cn.setRequestProperty("X-Emby-Token",token);return try{if(cn.responseCode!=200)throw Exception("HTTP ${cn.responseCode}");cn.inputStream.bufferedReader().use{it.readText()}}finally{cn.disconnect()}}
     val response=JSONObject(read("$server/Users/$user/Items?Recursive=true&IncludeItemTypes=$type&SearchTerm="+URLEncoder.encode(term,"UTF-8")+"&Fields=ProductionYear&Limit=60"))
     val array=response.getJSONArray("Items");val loaded=(0 until array.length()).map{array.getJSONObject(it)}
     activity.runOnUiThread {if(!closed&&generation==g){results=loaded;status=if(loaded.isEmpty())"Keine Treffer gefunden" else "${loaded.size} von ${response.optInt("TotalRecordCount",loaded.size)} Treffern";invalidate()}}
     loaded.forEach {obj->if(closed||generation!=g)return@thread;val id=obj.optString("Id")
      try{val cn=URL("$server/Items/$id/Images/Primary?maxWidth=320").openConnection() as HttpURLConnection;cn.connectTimeout=5000;cn.readTimeout=8000;cn.setRequestProperty("X-Emby-Token",token)
       val bitmap=try{cn.inputStream.use{BitmapFactory.decodeStream(it)}}finally{cn.disconnect()}
       if(bitmap!=null)activity.runOnUiThread{if(!closed&&generation==g){posters[id]=bitmap;invalidate()}}
      }catch(_:Exception){}
     }
    }catch(_:Exception){activity.runOnUiThread{if(!closed&&generation==g){status="Suche konnte nicht geladen werden";invalidate()}}}}}
    pending=task;postDelayed(task,350L)
   }
   fun open(){if(mode==2){val obj=results.getOrNull(selected)?:return;saveHistory();activity.startActivity(Intent(activity,EmbyDetailsActivity::class.java).apply{putExtra("item_id",obj.optString("Id"));putExtra("item_type",obj.optString("Type"));putExtra("item_title",obj.optString("Name"))});return}
    if(mode==1){if(selected>=history.take(8).size){if(history.isNotEmpty()){history=history.filterIndexed{i,_->i!=historyTarget};persistHistory()};selected=0;invalidate();return};query=history[selected].optString("term");mode=0;search();return}
    if(mode==3){filter=selected;search();return}
    when(val k=keys()[key]){"123","ABC"->{numeric=!numeric;key=0};"DEL"->{query=query.dropLast(1);search()};"SPACE"->{if(query.length<160)query+=" ";search()};else->{if(query.length<160)query+=k;search()}};invalidate()
   }
   override fun onKeyDown(code:Int,event:KeyEvent):Boolean{
    when(code){
     KeyEvent.KEYCODE_BACK,KeyEvent.KEYCODE_ESCAPE->dialog.dismiss()
     KeyEvent.KEYCODE_DPAD_CENTER,KeyEvent.KEYCODE_ENTER->if(event.repeatCount==0)open()
     KeyEvent.KEYCODE_DPAD_LEFT->when(mode){0->if(key==0&&history.isNotEmpty()){mode=1;selected=0}else key=(key-1+keys().size)%keys().size;1->{};2->if(selected>0)selected-- else if(history.isNotEmpty()){mode=1;selected=0};3->selected=(selected-1).coerceAtLeast(0)}
     KeyEvent.KEYCODE_DPAD_RIGHT->when(mode){0->key=(key+1)%keys().size;1->{mode=0;selected=0};2->selected=(selected+1).coerceAtMost((results.size-1).coerceAtLeast(0));3->selected=(selected+1).coerceAtMost(2)}
     KeyEvent.KEYCODE_DPAD_DOWN->when(mode){0->{mode=3;selected=filter};1->selected=(selected+1).coerceAtMost(history.take(8).size);3->if(results.isNotEmpty()){mode=2;selected=0};2->selected=(selected+5).coerceAtMost((results.size-1).coerceAtLeast(0))}
     KeyEvent.KEYCODE_DPAD_UP->when(mode){2->if(selected>=5)selected-=5 else {mode=3;selected=filter};3->{mode=0};1->if(selected>0)selected--else mode=0}
     KeyEvent.KEYCODE_DEL->{if(mode==1&&selected<history.size){history=history.filterIndexed{i,_->i!=selected};persistHistory();selected=0}else{query=query.dropLast(1);search()}}
     else->{val ch=event.unicodeChar;if(ch!=0&&!Character.isISOControl(ch)&&query.length<160){query+=ch.toChar();mode=0;search()}else return super.onKeyDown(code,event)}
    };if(mode==1&&selected<history.take(8).size)historyTarget=selected;invalidate();return true
   }
   init{isFocusable=true;isFocusableInTouchMode=true}
  }
  dialog.setContentView(view)
  dialog.setOnDismissListener{view.closed=true;view.generation++;view.pending?.let{view.removeCallbacks(it)}}
  dialog.window?.apply{setBackgroundDrawableResource(android.R.color.transparent);setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_HIDDEN or WindowManager.LayoutParams.SOFT_INPUT_ADJUST_NOTHING);addFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN);decorView.systemUiVisibility=View.SYSTEM_UI_FLAG_FULLSCREEN or View.SYSTEM_UI_FLAG_HIDE_NAVIGATION or View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY}
  dialog.show();dialog.window?.setLayout(WindowManager.LayoutParams.MATCH_PARENT,WindowManager.LayoutParams.MATCH_PARENT);view.requestFocus()
 }
}

'@
[IO.File]::WriteAllText((Join-Path $stage 'app\src\main\java\de\embyflow\androidtv\E2SearchKeyboard.kt'), $keyboard, $utf8)

$playerFile = Join-Path $stage 'app\src\main\java\de\embyflow\androidtv\EmbyPlayerActivity.kt'
$text = [IO.File]::ReadAllText($playerFile).Replace("`r`n", "`n")
$before = @'
        val exo = ExoPlayer.Builder(this).build()
'@
$after = @'
        stablePlayback = getSharedPreferences("embyflow", MODE_PRIVATE).getBoolean("stable_playback_v1", false)
        val builder = ExoPlayer.Builder(this)
        if (stablePlayback) {
            val memoryMiB = (getSystemService(ACTIVITY_SERVICE) as android.app.ActivityManager).memoryClass
            val targetBytes = (memoryMiB / 5).coerceIn(16, 64) * 1024 * 1024
            val loadControl = androidx.media3.exoplayer.DefaultLoadControl.Builder()
                .setBufferDurationsMs(60000, 120000, 8000, 15000)
                .setTargetBufferBytes(targetBytes)
                .setPrioritizeTimeOverSizeThresholds(false)
                .build()
            builder.setLoadControl(loadControl)
        }
        val exo = builder.build()
'@
$text = Replace-Once $text $before $after
$before = @'
    private var player: ExoPlayer? = null
'@
$after = @'
    private var player: ExoPlayer? = null
    private var stablePlayback = false
    private var recoveryAttempts = 0
    private var recoveryActive = true
    private var recoveryTask: Runnable? = null
    private var recoveryStatus = ""

    private fun retryNetworkFailure(error: PlaybackException): Boolean {
        if (!stablePlayback || !recoveryActive || playbackStopped || recoveryAttempts >= 3) return false
        // Never retry authentication, HTTP status, decoding or format failures.
        if (error.errorCode !in listOf(2001, 2002)) return false
        var cause: Throwable? = error
        var transientNetwork = false
        while (cause != null) {
            if (cause is androidx.media3.datasource.HttpDataSource.InvalidResponseCodeException) return false
            if (cause is java.net.SocketTimeoutException || cause is java.net.ConnectException ||
                cause is java.net.UnknownHostException || cause is java.net.SocketException) transientNetwork = true
            cause = cause.cause
        }
        if (!transientNetwork) return false
        val exo = player ?: return false
        val position = exo.currentPosition.coerceAtLeast(0L)
        val shouldPlay = exo.playWhenReady
        recoveryAttempts++
        recoveryStatus = "Verbindung wird wiederhergestellt ($recoveryAttempts/3)"
        controlsVisible = true
        recoveryTask?.let { handler.removeCallbacks(it) }
        val task = Runnable {
            recoveryTask = null
            if (recoveryActive && !isFinishing && !isDestroyed && !playbackStopped && player === exo) {
                exo.seekTo(position)
                exo.prepare()
                exo.playWhenReady = shouldPlay
            }
        }
        recoveryTask = task
        handler.postDelayed(task, recoveryAttempts * 2000L)
        overlay.invalidate()
        return true
    }

'@
$text = Replace-Once $text $before $after
$before = @'
            override fun onPlayerError(error: PlaybackException) {
                Toast.makeText(
'@
$after = @'
            override fun onPlayerError(error: PlaybackException) {
                if (retryNetworkFailure(error)) return
                recoveryStatus = "Wiedergabe unterbrochen"
                Toast.makeText(
'@
$text = Replace-Once $text $before $after
$before = @'
            override fun onPlaybackStateChanged(state: Int) {
                if (state == Player.STATE_READY
'@
$after = @'
            override fun onPlaybackStateChanged(state: Int) {
                if (state == Player.STATE_READY) recoveryStatus = ""
                if (state == Player.STATE_READY
'@
$text = Replace-Once $text $before $after
$before = @'
                if (videoInfo.isNotBlank()) "VIDEO $videoInfo" else ""
'@
$after = @'
                if (videoInfo.isNotBlank()) "VIDEO $videoInfo" else "",
                if (stablePlayback) "Puffer ${(exo?.totalBufferedDuration ?: 0L) / 1000}s" else "",
                recoveryStatus
'@
$text = Replace-Once $text $before $after
$before = @'
    override fun onStop() {
        sendPlaybackEvent("stopped")
'@
$after = @'
    override fun onStop() {
        recoveryActive = false
        recoveryTask?.let { handler.removeCallbacks(it) }
        recoveryTask = null
        sendPlaybackEvent("stopped")
'@
$text = Replace-Once $text $before $after
[IO.File]::WriteAllText($playerFile, $text, $utf8)
$manifest = Join-Path $stage 'app\src\main\AndroidManifest.xml'
$text = [IO.File]::ReadAllText($manifest)
$text = Replace-Once $text '<application android:allowBackup="true"' '<application android:allowBackup="false" android:usesCleartextTraffic="true"'
$text = Replace-Once $text "android:name=`".CinemaPlayerActivity`"`n        android:exported=`"true`"" "android:name=`".CinemaPlayerActivity`"`n        android:exported=`"false`""
[IO.File]::WriteAllText($manifest, $text, $utf8)
$gradle = Join-Path $stage 'app\build.gradle.kts'
$text = [IO.File]::ReadAllText($gradle)
$text = Replace-Once $text 'versionCode = 1' 'versionCode = 2026101610'
$text = Replace-Once $text 'versionName = "1.0"' 'versionName = "0.4.0-test10"'
[IO.File]::WriteAllText($gradle, $text, $utf8)
[IO.File]::WriteAllText((Join-Path $stage 'app\src\main\res\xml\backup_rules.xml'), '<full-backup-content><exclude domain="sharedpref" path="embyflow.xml" /></full-backup-content>', $utf8)
[IO.File]::WriteAllText((Join-Path $stage 'app\src\main\res\xml\data_extraction_rules.xml'), '<data-extraction-rules><cloud-backup><exclude domain="sharedpref" path="embyflow.xml" /></cloud-backup><device-transfer><exclude domain="sharedpref" path="embyflow.xml" /></device-transfer></data-extraction-rules>', $utf8)
if (!(Test-Path "$stage\gradlew.bat")) { throw 'Gradle-Wrapper fehlt.' }
$studioJava = 'C:\Program Files\Android\Android Studio\jbr'
if (Test-Path "$studioJava\bin\java.exe") { $env:JAVA_HOME = $studioJava }
$log = Join-Path $destination "EmbyFlowAndroid_Build_$stamp.log"
Push-Location $stage
try {
 & .\gradlew.bat --no-daemon :app:assembleDebug 2>&1 | Tee-Object -FilePath $log
 $buildExit = $LASTEXITCODE
} finally { Pop-Location }
if ($buildExit -ne 0) {
 explorer.exe "/select,`"$log`""
 throw "APK-Build fehlgeschlagen. Bitte die markierte Logdatei hier hochladen."
}
$built = Join-Path $stage 'app\build\outputs\apk\debug\app-debug.apk'
if (!(Test-Path $built)) { throw 'Keine APK gefunden.' }
$apk = Join-Path $destination "EmbyFlowAndroid_0.4.0-test10_$stamp.apk"
Copy-Item $built $apk
$hash = (Get-FileHash $apk -Algorithm SHA256).Hash
[IO.File]::WriteAllText("$apk.sha256", "$hash  $([IO.Path]::GetFileName($apk))`n", $utf8)
Write-Host "TEST-APK FERTIG: $apk" -ForegroundColor Green
$adb = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
if (!(Test-Path $adb)) { $adb = (Get-Command adb -ErrorAction Stop).Source }
$tv = '192.168.1.4:5555'
& $adb connect $tv
& $adb -s $tv install -r $apk
if ($LASTEXITCODE -ne 0) { throw 'APK gebaut, Installation fehlgeschlagen.' }
& $adb -s $tv shell am force-stop de.embyflow.androidtv
& $adb -s $tv shell am start -n de.embyflow.androidtv/.MainActivity
if ($LASTEXITCODE -ne 0) { throw 'App konnte nicht gestartet werden.' }
Start-Sleep -Seconds 4
$picture = Join-Path $destination "EmbyFlowAndroid_test10_$stamp.png"
& $adb -s $tv shell screencap -p /sdcard/embyflow_test10.png
if ($LASTEXITCODE -ne 0) { throw 'Screenshot fehlgeschlagen.' }
& $adb -s $tv pull /sdcard/embyflow_test10.png $picture
if ($LASTEXITCODE -ne 0) { throw 'Screenshot konnte nicht uebertragen werden.' }
& $adb -s $tv shell rm /sdcard/embyflow_test10.png
Start-Process $picture
explorer.exe "/select,`"$apk`""
