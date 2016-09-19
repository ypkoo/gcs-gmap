var map;
var startLatLng = {lat: 36.374092, lng: 127.365638}
var startLatLng2 = {lat: 36.374383, lng: 127.365327}
var marker;
var droneList = [];
var lineList = [];

var lineSymbol = {
	path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW
};

function struct_drone() {
	var marker = '';
	var id = '';
	var infoWindow = '';
}

function initMap() {
	map = new google.maps.Map(document.getElementById('map'), {
		center: startLatLng,
		zoom: 19,
		mapTypeId: google.maps.MapTypeId.HYBRID
	});

	// var image = 'images/drone.png';
	map.addListener('click', map_clicked);


	//test marker
	// var marker = new google.maps.Marker({
	// 	position: startLatLng,
	// 	map: map
	// });
}

function map_clicked(e) {
	var latLng = e.latLng;
	var lat = latLng.lat();
	var lng = latLng.lng();

	coordinateUpdater.update(lat, lng);
}

function update_marker(id, lat, lng) {
	// alert('hello-1');
	var idx = droneList.length;
	// alert(droneList);
	// alert('hello0');
	// existing drone
	for(var i=0; i<idx; i++) {
		if (id == droneList[i].id) {
			droneList[i].marker.setPosition({lat: lat, lng: lng});
			// droneList[i].infoWindow.setContent(infoString);
			return;
		}
	}

	// alert('hello1');

	// new drone
	var marker = new google.maps.Marker({
		position: {lat: lat, lng: lng},
		map: map
	});
	// alert('hello2');
	// var infoWindow = new google.maps.InfoWindow({
	//     content: ""
	// });
	// alert('hello3');
	// marker.addListener('click', function() {
	// 	infoWindow.open(map, marker);
	// });
	// alert('hello4');
	droneList[idx] = new struct_drone();
	droneList[idx].marker = marker;
	droneList[idx].id = id;
	// droneList[idx].infoWindow = infoWindow;
	// alert('hello');
}

function remove_marker(id) {
	for(var i=0; i<droneList.length; i++) {
		if (id == droneList[i].id) {
			droneList.marker.setMap(null);
			droneList[i] = null;
			break;
		}
	}
}

function remove_all_markers() {
	var idx = droneList.length;
	for (var i=0; i<idx; i++) {
		droneList[i].marker.setMap(null);
	}

	markerList = [];
}

function draw_line(startLat, startLng, endLat, endLng) {
	var line = new google.maps.Polyline({
		path: [{lat: startLat, lng: startLng}, {lat: endLat, lng: endLng}],
		icons: [{
			icon: lineSymbol,
			offset: '100%'
		}],
		// geodesic: true,
		// strokeColor: '#FF0000',
		// strokeOpacity: 1.0,
		// strokeWeight: 2,
		map: map
	});
	// console.log(startLat);

	// var lineCoordinate = [{lat: startLat, lng: startLng}, {lat: endLat, lng: endLng}];
 //  var line = new google.maps.Polyline({
 //    path: lineCoordinate,
 //    geodesic: true,
 //    strokeColor: '#FF0000',
 //    strokeOpacity: 1.0,
 //    strokeWeight: 2
 //  });

 //  line.setMap(map);



	lineList.push(line);
}

function remove_all_lines() {
	for (var i=0; i<lineList.length; i++) {
		lineList[i].setMap(null);
	}

	lineList = [];
}