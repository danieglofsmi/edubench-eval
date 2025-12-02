//https://echarts.apache.org/examples/en/editor.html?c=radar-custom
option = {
  color: ['#87CEEB', '#FFE434', '#56A3F1', '#FF917C', '#91CC75'],
  title: {
    text: 'Customized Radar Chart'
  },
  legend: {},
  radar: [
    {
      indicator: [
        { text: 'Idea Provision', max: 10, min: 5.8 },
        { text: 'Personalized Learning Support', max: 10, min: 5.8 },
        { text: 'Error Correction', max: 10, min: 5.8 },
        { text: 'Problem Solving', max: 10, min: 5.8 },
        { text: 'Automatic Grading', max: 10, min: 5.8 },
        { text: 'Teaching Material Generation', max: 10, min: 5.8 },
        { text: 'Emotional Support', max: 10, min: 5.8 },
        { text: 'Question Generation', max: 10, min: 5.8 },
        { text: 'Personalized Content Creation', max: 10, min: 5.8 }
      ],
      center: ['50%', '75%'],
      radius: 120,
      startAngle: 90,
      splitNumber: 4,
      shape: 'circle',
      axisName: {
        formatter: '{value}',
        color: '#428BD4',
        fontStyle: 'Consolas'
      }
    },
    {
      indicator: [
        { text: 'BFA', max: 10, min: 5.5 },
        { text: 'CSI', max: 10, min: 5.5 },
        { text: 'CRSC', max: 10, min: 5.5 },
        { text: 'EICP', max: 10, min: 5.5 },
        { text: 'IFTC', max: 10, min: 5.5 },
        { text: 'MGP', max: 10, min: 5.5 },
        { text: 'PAS', max: 10, min: 5.5 },
        { text: 'RPR', max: 10, min: 5.5 },
        { text: 'RTC', max: 10, min: 5.5 },
        { text: 'SEI', max: 10, min: 5.5}
      ],
      center: ['50%', '25%'],
      radius: 120,
      axisName: {
        color: '#56A3F1',
        fontStyle: 'Consolas'
      }
    }
  ],
  series: [
    {
      type: 'radar',
      emphasis: {
        lineStyle: {
          width: 4
        }
      },
      data: [
        {
          value: [7.17, 9.11, 8.71, 8.8, 8.42, 8.86, 9.15, 8.79, 9.35],
          name: 'DeepSeek R1'
        },
        {
          value: [7.45, 8.12, 8.16, 8.17, 7.84, 7.56, 8.08, 8.01, 7.03],
          name: 'DeepSeek V3'
        },
        {
          value: [7.72, 7.94, 8.21, 8.15, 7.89, 7.99, 7.85, 8.39, 8.42],
          name: 'Qwen Max'
        },
        {
          value: [7.66, 7.38, 7.92, 7.56, 7.55, 7.84, 7.31, 7.91, 7.36],
          name: 'Qwen2.5-14B-Instruct'
        },
        {
          value: [6.78, 7.63, 7.93, 7.74, 6.79, 7.86, 7.79, 7.55, 7.42],
          name: 'Qwen2.5-7B-Instruct',
          areaStyle: {
            color: 'rgba(255, 145, 124, 0.1)'
          }
        }
      ]
    },
    {
      type: 'radar',
      radarIndex: 1,
      data: [
        {
          value: [
            8.97, 8.6, 8.98, 8.94, 8.86, 8.56, 8.77, 8.2, 9.26, 7.95, 8.91, 8.92
          ],
          name: 'DeepSeek R1'
        },
        {
          value: [
            8.77, 7.77, 8.4, 7.89, 8.11, 7.25, 8.1, 7.7, 7.42, 7.03, 7.8, 7.47
          ],
          name: 'DeepSeek V3'
        },
        {
          value: [
            8.81, 8.01, 8.52, 8.27, 8.23, 7.59, 8.1, 7.7, 7.89, 7.31, 8.09, 7.74
          ],
          name: 'Qwen Max'
        },
        {
          value: [
            8.74, 7.76, 8.26, 7.79, 7.86, 6.88, 7.77, 6.97, 7.02, 7.01, 7.59,
            7.03
          ],
          name: 'Qwen2.5-14B-Instruct'
        },
        {
          value: [
            8.49, 7.63, 8.04, 7.82, 7.45, 6.93, 7.65, 7.05, 7.38, 5.9, 7.82, 7.35
          ],
          name: 'Qwen2.5-7B-Instruct',
          areaStyle: {
            color: 'rgba(255, 145, 124, 0.1)'
          }
        }
      ]
    }
  ]
};
