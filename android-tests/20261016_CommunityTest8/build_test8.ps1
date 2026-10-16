$ErrorActionPreference = 'Stop'
$project = 'C:\Users\bumse\AndroidStudioProjects\EmbyFlowAndroid'
$destination = 'C:\Users\bumse\Downloads\TCL'
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$stage = Join-Path $destination "EmbyFlowAndroid_CommunityTest_$stamp"
$utf8 = New-Object System.Text.UTF8Encoding($false)
$expected = @{
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
[IO.File]::WriteAllText($main, $text, $utf8)
$keyboard = @'
package de.embyflow.androidtv

import android.app.Activity
import android.app.Dialog
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Typeface
import android.view.KeyEvent
import android.view.MotionEvent
import android.view.View
import android.view.Window
import android.view.WindowManager
import kotlin.math.abs

internal object E2SearchKeyboard {
    fun show(activity: Activity, accept: (String) -> Unit) {
        val dialog = Dialog(activity)
        dialog.requestWindowFeature(Window.FEATURE_NO_TITLE)
        val keyboard = object : View(activity) {
            val rows = listOf(
                listOf("1","2","3","4","5","6","7","8","9","0","ß","DEL"),
                listOf("q","w","e","r","t","z","u","i","o","p","ü"),
                listOf("a","s","d","f","g","h","j","k","l","ö","ä"),
                listOf("SHIFT","y","x","c","v","b","n","m",",",".","-","ENTER"),
                listOf("LEERTASTE","SUCHEN"))
            val boxes = rows.mapIndexed { row, keys ->
                keys.mapIndexed { col, _ ->
                    if (row == 4) {
                        if (col == 0) RectF(380f,836f,1310f,920f) else RectF(1340f,828f,1670f,920f)
                    } else {
                        val start = listOf(154f,220f,250f,190f)[row]
                        val y = 328f + row * 120f + (abs(col - (keys.size - 1)/2f)*3f).toInt()
                        RectF(start+col*128f,y,start+col*128f+118f,y+84f)
                    }
                }
            }
            val pen = Paint(Paint.ANTI_ALIAS_FLAG)
            var row = 1
            var col = 0
            var upper = false
            var value = ""
            val navy = Color.rgb(12,24,39)
            val cyan = Color.rgb(35,215,255)
            init { isFocusableInTouchMode = true; isFocusable = true }
            fun label(c: Canvas, text: String, x: Float, y: Float, size: Float, color: Int = Color.WHITE, bold: Boolean = false) {
                pen.style = Paint.Style.FILL; pen.color = color; pen.textSize = size
                pen.typeface = if (bold) Typeface.DEFAULT_BOLD else Typeface.DEFAULT
                c.drawText(text,x,y,pen)
            }
            fun submit() {
                val query = value.trim()
                if (query.isNotEmpty()) { dialog.dismiss(); accept(query) }
            }
            fun choose() {
                when(val key = rows[row][col]) {
                    "SHIFT" -> upper = !upper
                    "DEL" -> if (value.isNotEmpty()) value = value.dropLast(1)
                    "ENTER", "SUCHEN" -> submit()
                    "LEERTASTE" -> if (value.length < 160) value += " "
                    else -> if (value.length < 160) value += if (upper) key.uppercase(java.util.Locale.GERMANY) else key
                }
                invalidate()
            }
            override fun onDraw(c: Canvas) {
                c.save(); c.scale(width/1920f,height/1080f); c.drawColor(navy)
                label(c,"EmbyFlow",90f,74f,32f,Color.rgb(194,203,214))
                label(c,"EmbyFlow Suche",90f,139f,42f,bold=true)
                pen.color = Color.rgb(52,65,80); pen.style = Paint.Style.STROKE; pen.strokeWidth = 2f
                c.drawRoundRect(RectF(90f,174f,1830f,264f),12f,12f,pen)
                c.save(); c.clipRect(108f,180f,1810f,260f)
                pen.textSize = 38f; pen.typeface = Typeface.DEFAULT
                val shown = value + "│"
                val textX = (1808f-pen.measureText(shown)).coerceAtMost(110f)
                label(c,shown,textX,233f,38f); c.restore()
                label(c,if (upper) "Großbuchstaben" else "Kleinbuchstaben",90f,299f,21f,Color.rgb(127,139,153))
                rows.forEachIndexed { r, keys -> keys.forEachIndexed { k, key ->
                    val box = boxes[r][k]
                    pen.style = Paint.Style.FILL
                    pen.color = if (r == row && k == col) cyan else if (key == "SUCHEN") Color.rgb(13,83,45) else navy
                    c.drawRoundRect(box,10f,10f,pen)
                    pen.style = Paint.Style.STROKE; pen.strokeWidth = 1f; pen.color = Color.rgb(52,65,80)
                    c.drawRoundRect(box,10f,10f,pen)
                    val text = when(key) { "SHIFT" -> "⇧"; "DEL" -> "⌫"; "ENTER" -> "↵"; else -> if (upper && key.length == 1) key.uppercase(java.util.Locale.GERMANY) else key }
                    pen.textSize = if (r == 4) 27f else 28f; pen.typeface = Typeface.DEFAULT_BOLD
                    val x = box.centerX() - pen.measureText(text)/2f
                    label(c,text,x,box.centerY()+10f,pen.textSize,if (r == row && k == col) navy else Color.rgb(230,236,243),true)
                } }
                label(c,"Pfeile: Auswahl    OK: Taste übernehmen    Zurück: Abbrechen",90f,1016f,23f,Color.rgb(220,226,233))
                c.restore()
            }
            override fun onKeyDown(code: Int, event: KeyEvent): Boolean {
                when(code) {
                    KeyEvent.KEYCODE_DPAD_LEFT -> col = (col-1).coerceAtLeast(0)
                    KeyEvent.KEYCODE_DPAD_RIGHT -> col = (col+1).coerceAtMost(rows[row].lastIndex)
                    KeyEvent.KEYCODE_DPAD_UP,KeyEvent.KEYCODE_DPAD_DOWN -> {
                        val x = boxes[row][col].centerX()
                        row = (row + if(code == KeyEvent.KEYCODE_DPAD_UP) -1 else 1).coerceIn(0,rows.lastIndex)
                        col = boxes[row].indices.minByOrNull { abs(boxes[row][it].centerX()-x) } ?: 0
                    }
                    KeyEvent.KEYCODE_DPAD_CENTER,KeyEvent.KEYCODE_ENTER,KeyEvent.KEYCODE_NUMPAD_ENTER -> if(event.repeatCount == 0) choose()
                    KeyEvent.KEYCODE_BACK,KeyEvent.KEYCODE_ESCAPE -> dialog.dismiss()
                    KeyEvent.KEYCODE_DEL -> { if(value.isNotEmpty()) value=value.dropLast(1) }
                    else -> {
                        val ch=event.unicodeChar
                        if(ch != 0 && !Character.isISOControl(ch) && value.length < 160) value += ch.toChar() else return super.onKeyDown(code,event)
                    }
                }
                invalidate(); return true
            }
            override fun onTouchEvent(event: MotionEvent): Boolean {
                if(event.action == MotionEvent.ACTION_DOWN) {
                    val x=event.x*1920f/width; val y=event.y*1080f/height
                    boxes.forEachIndexed { r, line -> line.forEachIndexed { k, box -> if(box.contains(x,y)) { row=r;col=k;choose();return true } } }
                }
                return true
            }
        }
        dialog.setContentView(keyboard)
        dialog.window?.apply {
            setBackgroundDrawableResource(android.R.color.transparent)
            setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_HIDDEN or WindowManager.LayoutParams.SOFT_INPUT_ADJUST_NOTHING)
            addFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN)
            decorView.systemUiVisibility = View.SYSTEM_UI_FLAG_FULLSCREEN or View.SYSTEM_UI_FLAG_HIDE_NAVIGATION or View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
        }
        dialog.show()
        dialog.window?.setLayout(WindowManager.LayoutParams.MATCH_PARENT,WindowManager.LayoutParams.MATCH_PARENT)
        keyboard.requestFocus()
    }
}

'@
[IO.File]::WriteAllText((Join-Path $stage 'app\src\main\java\de\embyflow\androidtv\E2SearchKeyboard.kt'), $keyboard, $utf8)

$manifest = Join-Path $stage 'app\src\main\AndroidManifest.xml'
$text = [IO.File]::ReadAllText($manifest)
$text = Replace-Once $text '<application android:allowBackup="true"' '<application android:allowBackup="false" android:usesCleartextTraffic="true"'
$text = Replace-Once $text "android:name=`".CinemaPlayerActivity`"`n        android:exported=`"true`"" "android:name=`".CinemaPlayerActivity`"`n        android:exported=`"false`""
[IO.File]::WriteAllText($manifest, $text, $utf8)
$gradle = Join-Path $stage 'app\build.gradle.kts'
$text = [IO.File]::ReadAllText($gradle)
$text = Replace-Once $text 'versionCode = 1' 'versionCode = 2026101608'
$text = Replace-Once $text 'versionName = "1.0"' 'versionName = "0.4.0-test8"'
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
$apk = Join-Path $destination "EmbyFlowAndroid_0.4.0-test8_$stamp.apk"
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
$picture = Join-Path $destination "EmbyFlowAndroid_test8_$stamp.png"
& $adb -s $tv shell screencap -p /sdcard/embyflow_test8.png
if ($LASTEXITCODE -ne 0) { throw 'Screenshot fehlgeschlagen.' }
& $adb -s $tv pull /sdcard/embyflow_test8.png $picture
if ($LASTEXITCODE -ne 0) { throw 'Screenshot konnte nicht uebertragen werden.' }
& $adb -s $tv shell rm /sdcard/embyflow_test8.png
Start-Process $picture
explorer.exe "/select,`"$apk`""
