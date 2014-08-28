
<div class="thumbnail filter-collection-record">
      <img src="{{record.get('files')[0].get('url')}}" />
      <div class="caption">
        
        <h5><a href="{{ url_for('record.metadata', recid=record['recid']) }}"> {{ record.get('title.title', '') }}</a>  </h5>
        {% if record.get('abstract')%}
        <p>{{record.get('abstract.summary')|sentences(2)}}[...]</p>
        {%else %}
        No description
        {%endif%}
      </div>
</div>

















