package com.mabinogi.dyehelper

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.media.projection.MediaProjectionManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.widget.SeekBar
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import com.mabinogi.dyehelper.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var mediaProjectionManager: MediaProjectionManager

    private var color1 = Color.parseColor("#515E5B")
    private var color2 = Color.parseColor("#7B6655")
    private var color3 = Color.parseColor("#E2B174")
    private var tolerance = 30

    private val overlayPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) {
        if (Settings.canDrawOverlays(this)) {
            requestMediaProjection()
        } else {
            Toast.makeText(this, "오버레이 권한이 필요합니다", Toast.LENGTH_SHORT).show()
        }
    }

    private val mediaProjectionLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK && result.data != null) {
            startFloatingService(result.resultCode, result.data!!)
        } else {
            Toast.makeText(this, "화면 캡처 권한이 필요합니다", Toast.LENGTH_SHORT).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        mediaProjectionManager = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager

        loadSettings()
        setupUI()
    }

    private fun loadSettings() {
        val prefs = getSharedPreferences("dye_helper", Context.MODE_PRIVATE)
        color1 = prefs.getInt("color1", color1)
        color2 = prefs.getInt("color2", color2)
        color3 = prefs.getInt("color3", color3)
        tolerance = prefs.getInt("tolerance", tolerance)
    }

    private fun saveSettings() {
        val prefs = getSharedPreferences("dye_helper", Context.MODE_PRIVATE)
        prefs.edit().apply {
            putInt("color1", color1)
            putInt("color2", color2)
            putInt("color3", color3)
            putInt("tolerance", tolerance)
            apply()
        }
    }

    private fun setupUI() {
        // 색상 버튼 설정
        updateColorButtons()

        binding.btnColor1.setOnClickListener { showColorPicker(1) }
        binding.btnColor2.setOnClickListener { showColorPicker(2) }
        binding.btnColor3.setOnClickListener { showColorPicker(3) }

        // 허용 오차 슬라이더
        binding.seekTolerance.progress = tolerance
        binding.tvTolerance.text = "허용 오차: $tolerance"
        binding.seekTolerance.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                tolerance = progress
                binding.tvTolerance.text = "허용 오차: $tolerance"
            }
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {
                saveSettings()
            }
        })

        // 시작 버튼
        binding.btnStart.setOnClickListener {
            saveSettings()
            checkAndRequestPermissions()
        }

        // 중지 버튼
        binding.btnStop.setOnClickListener {
            stopFloatingService()
        }
    }

    private fun updateColorButtons() {
        binding.btnColor1.setBackgroundColor(color1)
        binding.btnColor2.setBackgroundColor(color2)
        binding.btnColor3.setBackgroundColor(color3)

        binding.tvColor1.text = String.format("#%06X", 0xFFFFFF and color1)
        binding.tvColor2.text = String.format("#%06X", 0xFFFFFF and color2)
        binding.tvColor3.text = String.format("#%06X", 0xFFFFFF and color3)
    }

    private fun showColorPicker(colorIndex: Int) {
        val currentColor = when (colorIndex) {
            1 -> color1
            2 -> color2
            else -> color3
        }

        val input = android.widget.EditText(this)
        input.setText(String.format("#%06X", 0xFFFFFF and currentColor))

        AlertDialog.Builder(this)
            .setTitle("색상 입력 (예: #FF5500)")
            .setView(input)
            .setPositiveButton("확인") { _, _ ->
                try {
                    val newColor = Color.parseColor(input.text.toString())
                    when (colorIndex) {
                        1 -> color1 = newColor
                        2 -> color2 = newColor
                        3 -> color3 = newColor
                    }
                    updateColorButtons()
                    saveSettings()
                } catch (e: Exception) {
                    Toast.makeText(this, "잘못된 색상 형식입니다", Toast.LENGTH_SHORT).show()
                }
            }
            .setNegativeButton("취소", null)
            .show()
    }

    private fun checkAndRequestPermissions() {
        if (!Settings.canDrawOverlays(this)) {
            AlertDialog.Builder(this)
                .setTitle("권한 필요")
                .setMessage("다른 앱 위에 표시 권한이 필요합니다.")
                .setPositiveButton("설정으로 이동") { _, _ ->
                    val intent = Intent(
                        Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                        Uri.parse("package:$packageName")
                    )
                    overlayPermissionLauncher.launch(intent)
                }
                .setNegativeButton("취소", null)
                .show()
        } else {
            requestMediaProjection()
        }
    }

    private fun requestMediaProjection() {
        val intent = mediaProjectionManager.createScreenCaptureIntent()
        mediaProjectionLauncher.launch(intent)
    }

    private fun startFloatingService(resultCode: Int, data: Intent) {
        val intent = Intent(this, FloatingService::class.java).apply {
            putExtra("resultCode", resultCode)
            putExtra("data", data)
            putExtra("color1", color1)
            putExtra("color2", color2)
            putExtra("color3", color3)
            putExtra("tolerance", tolerance)
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }

        Toast.makeText(this, "서비스 시작됨", Toast.LENGTH_SHORT).show()
    }

    private fun stopFloatingService() {
        stopService(Intent(this, FloatingService::class.java))
        Toast.makeText(this, "서비스 중지됨", Toast.LENGTH_SHORT).show()
    }
}
