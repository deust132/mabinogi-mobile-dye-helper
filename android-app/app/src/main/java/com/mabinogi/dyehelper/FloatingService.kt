package com.mabinogi.dyehelper

import android.app.*
import android.content.Context
import android.content.Intent
import android.graphics.*
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.Image
import android.media.ImageReader
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.util.DisplayMetrics
import android.view.*
import android.widget.ImageButton
import android.widget.Toast
import androidx.core.app.NotificationCompat

class FloatingService : Service() {

    private lateinit var windowManager: WindowManager
    private lateinit var floatingView: View
    private lateinit var guideView: GuideOverlayView

    private var mediaProjection: MediaProjection? = null
    private var virtualDisplay: VirtualDisplay? = null
    private var imageReader: ImageReader? = null

    private var color1 = Color.parseColor("#515E5B")
    private var color2 = Color.parseColor("#7B6655")
    private var color3 = Color.parseColor("#E2B174")
    private var tolerance = 30

    private var screenWidth = 0
    private var screenHeight = 0
    private var screenDensity = 0

    private val handler = Handler(Looper.getMainLooper())

    // 가이드라인 위치 (화면 비율로 저장)
    private var guide1X = 0.3f
    private var guide2X = 0.5f
    private var guide3X = 0.7f

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        windowManager = getSystemService(Context.WINDOW_SERVICE) as WindowManager

        val metrics = DisplayMetrics()
        windowManager.defaultDisplay.getMetrics(metrics)
        screenWidth = metrics.widthPixels
        screenHeight = metrics.heightPixels
        screenDensity = metrics.densityDpi

        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        intent?.let {
            color1 = it.getIntExtra("color1", color1)
            color2 = it.getIntExtra("color2", color2)
            color3 = it.getIntExtra("color3", color3)
            tolerance = it.getIntExtra("tolerance", tolerance)

            val resultCode = it.getIntExtra("resultCode", Activity.RESULT_CANCELED)
            val data = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                it.getParcelableExtra("data", Intent::class.java)
            } else {
                @Suppress("DEPRECATION")
                it.getParcelableExtra("data")
            }

            if (resultCode != Activity.RESULT_CANCELED && data != null) {
                startForeground(NOTIFICATION_ID, createNotification())
                setupMediaProjection(resultCode, data)
                createFloatingButton()
                createGuideOverlay()
            }
        }

        return START_NOT_STICKY
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "염색 도우미",
                NotificationManager.IMPORTANCE_LOW
            )
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    private fun createNotification(): Notification {
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("마비노기 염색 도우미")
            .setContentText("실행 중...")
            .setSmallIcon(android.R.drawable.ic_menu_camera)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }

    private fun setupMediaProjection(resultCode: Int, data: Intent) {
        val manager = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        mediaProjection = manager.getMediaProjection(resultCode, data)

        imageReader = ImageReader.newInstance(
            screenWidth, screenHeight,
            PixelFormat.RGBA_8888, 2
        )

        virtualDisplay = mediaProjection?.createVirtualDisplay(
            "DyeHelper",
            screenWidth, screenHeight, screenDensity,
            DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
            imageReader?.surface, null, null
        )
    }

    private fun createFloatingButton() {
        val layoutFlag = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        } else {
            @Suppress("DEPRECATION")
            WindowManager.LayoutParams.TYPE_PHONE
        }

        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            layoutFlag,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
            PixelFormat.TRANSLUCENT
        )
        params.gravity = Gravity.TOP or Gravity.START
        params.x = 0
        params.y = 100

        floatingView = LayoutInflater.from(this).inflate(R.layout.floating_button, null)

        val btnCapture = floatingView.findViewById<ImageButton>(R.id.btn_capture)
        val btnGuide = floatingView.findViewById<ImageButton>(R.id.btn_guide)
        val btnClose = floatingView.findViewById<ImageButton>(R.id.btn_close)

        btnCapture.setOnClickListener { captureAndAnalyze() }
        btnGuide.setOnClickListener { toggleGuide() }
        btnClose.setOnClickListener { stopSelf() }

        // 드래그로 이동
        setupDrag(floatingView, params)

        windowManager.addView(floatingView, params)
    }

    private fun createGuideOverlay() {
        val layoutFlag = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        } else {
            @Suppress("DEPRECATION")
            WindowManager.LayoutParams.TYPE_PHONE
        }

        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            layoutFlag,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                    WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE or
                    WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        )

        guideView = GuideOverlayView(this)
        guideView.setGuidePositions(guide1X, guide2X, guide3X)
        guideView.visibility = View.GONE

        windowManager.addView(guideView, params)
    }

    private fun setupDrag(view: View, params: WindowManager.LayoutParams) {
        var initialX = 0
        var initialY = 0
        var initialTouchX = 0f
        var initialTouchY = 0f

        view.setOnTouchListener { _, event ->
            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    initialX = params.x
                    initialY = params.y
                    initialTouchX = event.rawX
                    initialTouchY = event.rawY
                    true
                }
                MotionEvent.ACTION_MOVE -> {
                    params.x = initialX + (event.rawX - initialTouchX).toInt()
                    params.y = initialY + (event.rawY - initialTouchY).toInt()
                    windowManager.updateViewLayout(view, params)
                    true
                }
                else -> false
            }
        }
    }

    private fun toggleGuide() {
        guideView.visibility = if (guideView.visibility == View.VISIBLE) {
            View.GONE
        } else {
            View.VISIBLE
        }
    }

    private fun captureAndAnalyze() {
        val image = imageReader?.acquireLatestImage()
        if (image == null) {
            Toast.makeText(this, "캡처 실패", Toast.LENGTH_SHORT).show()
            return
        }

        val bitmap = imageToBitmap(image)
        image.close()

        if (bitmap != null) {
            analyzeColors(bitmap)
        }
    }

    private fun imageToBitmap(image: Image): Bitmap? {
        val planes = image.planes
        val buffer = planes[0].buffer
        val pixelStride = planes[0].pixelStride
        val rowStride = planes[0].rowStride
        val rowPadding = rowStride - pixelStride * screenWidth

        val bitmap = Bitmap.createBitmap(
            screenWidth + rowPadding / pixelStride,
            screenHeight,
            Bitmap.Config.ARGB_8888
        )
        bitmap.copyPixelsFromBuffer(buffer)

        return Bitmap.createBitmap(bitmap, 0, 0, screenWidth, screenHeight)
    }

    private fun analyzeColors(bitmap: Bitmap) {
        val targetColors = listOf(color1, color2, color3)
        val foundPositions = mutableListOf<Pair<Int, Int>>()

        // 샘플링으로 분석 (성능을 위해)
        val step = 10
        for (y in 0 until bitmap.height step step) {
            for (x in 0 until bitmap.width step step) {
                val pixel = bitmap.getPixel(x, y)
                for (target in targetColors) {
                    if (isColorMatch(pixel, target, tolerance)) {
                        foundPositions.add(Pair(x, y))
                        break
                    }
                }
            }
        }

        handler.post {
            if (foundPositions.isNotEmpty()) {
                Toast.makeText(this, "색상 ${foundPositions.size}개 위치 발견!", Toast.LENGTH_SHORT).show()
                guideView.setDetectedPositions(foundPositions)
                guideView.visibility = View.VISIBLE
            } else {
                Toast.makeText(this, "일치하는 색상 없음", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun isColorMatch(pixel: Int, target: Int, tolerance: Int): Boolean {
        val r1 = Color.red(pixel)
        val g1 = Color.green(pixel)
        val b1 = Color.blue(pixel)

        val r2 = Color.red(target)
        val g2 = Color.green(target)
        val b2 = Color.blue(target)

        return kotlin.math.abs(r1 - r2) <= tolerance &&
                kotlin.math.abs(g1 - g2) <= tolerance &&
                kotlin.math.abs(b1 - b2) <= tolerance
    }

    override fun onDestroy() {
        super.onDestroy()
        try {
            windowManager.removeView(floatingView)
            windowManager.removeView(guideView)
        } catch (e: Exception) {}

        virtualDisplay?.release()
        imageReader?.close()
        mediaProjection?.stop()
    }

    companion object {
        private const val CHANNEL_ID = "dye_helper_channel"
        private const val NOTIFICATION_ID = 1001
    }
}
