// https://echarts.apache.org/examples/en/editor.html?c=sunburst-drink
var data = [
  {
    name: 'Student Oriented',
    children: [
      {
        name: 'Problem Solving',
        children: [
          { name: 'Instruction Following & Task Completion', value: 1 },
          { name: 'Content Relevance & Scope Control', value: 1 },
          { name: 'Scenario Element Integration', value: 1 },
          { name: 'Basic Factual Accuracy', value: 1 },
          { name: 'Domain Knowledge Accuracy', value: 1 },
          { name: 'Reasoning Process Rigor', value: 1 },
          { name: 'Clarity, Simplicity & Inspiration', value: 1 },
          { name: 'Higher-Order Thinking & Skill Development', value: 1 }
        ]
      },
      {
        name: 'Error Correction',
        children: [
          { name: 'Instruction Following & Task Completion', value: 1 },
          { name: 'Scenario Element Integration', value: 1 },
          { name: 'Basic Factual Accuracy', value: 1 },
          { name: 'Reasoning Process Rigor', value: 1 },
          { name: 'Error Identification & Correction Precision', value: 1 },
          { name: 'Clarity, Simplicity & Inspiration', value: 1 },
          { name: 'Motivation, Guidance & Positive Feedback', value: 1 }
        ]
      },
      {
        name: 'Idea Provision',
        value: 5,
        children: [
          { name: 'Instruction Following & Task Completion', value: 1.25 },
          { name: 'Basic Factual Accuracy', value: 1.25 },
          { name: 'Content Relevance & Scope Control', value: 1.25 },
          { name: 'Reasoning Process Rigor', value: 1.25 }
        ]
      },
      {
        name: 'Personalized Learning Support',
        value: 7.5,
        children: [
          { name: 'Instruction Following & Task Completion', value: 1.5 },
          { name: 'Role & Tone Consistency', value: 1.5 },
          { name: 'Scenario Element Integration', value: 1.5 },
          { name: 'Personalization, Adaptation & Learning Support', value: 1.5 },
          { name: 'Higher-Order Thinking & Skill Development', value: 1.5 }
        ]
      },
      {
        name: 'Emotional Support',
        value: 5.5,
        children: [
          { name: 'Instruction Following & Task Completion', value: 1.1 },
          { name: 'Role & Tone Consistency', value: 1.1 },
          { name: 'Scenario Element Integration', value: 1.1 },
          { name: 'Motivation, Guidance & Positive Feedback', value: 1.1 },
          { name: 'Personalization, Adaptation & Learning Support', value: 1.1 }
        ]
      }
    ]
  },
  {
    name: 'Teacher Oriented',
    children: [
      {
        name: 'Question Generation',
        children: [
          { name: 'Instruction Following & Task Completion', value: 1 },
          { name: 'Content Relevance & Scope Control', value: 1 },
          { name: 'Basic Factual Accuracy', value: 1 },
          { name: 'Domain Knowledge Accuracy', value: 1 },
          { name: 'Clarity, Simplicity & Inspiration', value: 1 },
          { name: 'Higher-Order Thinking & Skill Development', value: 1 }
        ]
      },
      {
        name: 'Automatic Grading',
        children: [
          { name: 'Instruction Following & Task Completion', value: 1 },
          { name: 'Content Relevance & Scope Control', value: 1 },
          { name: 'Basic Factual Accuracy', value: 1 },
          { name: 'Reasoning Process Rigor', value: 1 },
          { name: 'Error Identification & Correction Precision', value: 1 },
          { name: 'Motivation, Guidance & Positive Feedback', value: 1 }
        ]
      },
      {
        name: 'Teaching Material Generation',
        children: [
          { name: 'Instruction Following & Task Completion', value: 1 },
          { name: 'Role & Tone Consistency', value: 1 },
          { name: 'Content Relevance & Scope Control', value: 1 },
          { name: 'Basic Factual Accuracy', value: 1 },
          { name: 'Domain Knowledge Accuracy', value: 1 },
          { name: 'Clarity, Simplicity & Inspiration', value: 1 },
          { name: 'Higher-Order Thinking & Skill Development', value: 1 }
        ]
      },
      {
        name: 'Personalized Content Creation',
        value: 6,
        children: [
          { name: 'Instruction Following & Task Completion', value: 2 },
          { name: 'Scenario Element Integration', value: 2 },
          { name: 'Personalization, Adaptation & Learning Support', value: 2 }
        ]
      }
    ]
  }
];
option = {
  series: [{
    type: 'sunburst',
    data: data,
    label: {
      rotate: 'radius'
    },
    levels: [
      {},
      {
        r0: '0%',
        r: '20%',
        itemStyle: {
          borderWidth: 2
        },
        // label:{
        //   show: false,
        // }
        label: {
          fontFamily: 'Calibri',
          fontStyle: 'bold',
          fontSize: 14,
          lineHeight: 20, // 设置行高
          padding: [5, 10], // 设置内边距
          formatter: function (params) {
            var text = params.name;
            var lines = text.split(' ');
            return lines.join('\n');
          }
        }
      },
      {
        r0: '20%',
        r: '50%',
        // label:{
        //   show: false,
        // }
        label: {
          fontFamily: 'Calibri',
          fontSize: 14,
          fontStyle: 'bold',
          lineHeight: 20, // 设置行高
          padding: [5, 10], // 设置内边距
          formatter: function (params) {
            var text = params.name;
            var lines = text.split(' ');
            return lines.join('\n');
          }
        }
      },
      {
        r0: '70%',
        r: '75%',
        // label:{
        //   show: false,
        // },
        label: {
          fontFamily: 'Calibri',
          fontSize: 12,
          position: 'outside',
          padding: [5, 10],
          rotate:'radius',
          silent: false
        },
        itemStyle: {
          borderWidth: 3
        }
      }
    ]
  },
  {
      name: 'context',
      type: 'pie',
      radius: ['50%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 10,
        borderColor: '#fff',
        borderWidth: 5,
        // color: '#E2F0D9'
      },
      
      label:{
          show: false,
      },
      
      data: [
        { value: 2000, name: 'grade' ,itemStyle: { color: '#5470C6' }},
        { value: 500, name: 'question type' ,itemStyle: { color: '#91CC75' }},
        { value: 300, name: 'language' ,itemStyle: { color: '#F2B800' }},
        { value: 300, name: 'difficulty' ,itemStyle: { color: '#EE6666' }}
      ]
    }]

};
